"""
TRUSTRAG — Secrets Manager with Multi-Backend Support.

Supports:
1. Environment variables (primary, zero-config)
2. HashiCorp Vault via hvac (production)
3. SOPS/age encrypted files (local development, CI/CD)
4. .env file loading (fallback)

All backends are optional — gracefully falls back to environment variables.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ─── Secret Backend Interface ─────────────────────────────────────────────────


class SecretBackend(ABC):
    """Abstract base class for secret backends."""

    @abstractmethod
    def get_secret(self, key: str) -> str | None:
        """Get a secret value by key. Returns None if not found."""
        pass

    @abstractmethod
    def get_secrets(self, prefix: str = "") -> dict[str, str]:
        """Get all secrets with optional prefix filter."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name for logging."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether this backend is configured and available."""
        pass


# ─── Environment Variable Backend ─────────────────────────────────────────────


class EnvBackend(SecretBackend):
    """Environment variable backend (always available)."""

    @property
    def name(self) -> str:
        return "environment"

    @property
    def is_available(self) -> bool:
        return True

    def get_secret(self, key: str) -> str | None:
        return os.environ.get(key)

    def get_secrets(self, prefix: str = "") -> dict[str, str]:
        if prefix:
            return {k: v for k, v in os.environ.items() if k.startswith(prefix)}
        return dict(os.environ)


# ─── .env File Backend ────────────────────────────────────────────────────────


class DotEnvBackend(SecretBackend):
    """Loads secrets from .env file using python-dotenv."""

    def __init__(self, env_path: Path | None = None):
        self._env_path = env_path or self._find_env_file()
        self._secrets: dict[str, str] = {}
        self._loaded = False

    def _find_env_file(self) -> Path | None:
        """Search for .env file in common locations."""
        search_paths = [
            Path.cwd() / ".env",
            Path.cwd().parent / ".env",
            Path.cwd().parent.parent / ".env",
            Path(__file__).resolve().parents[3] / ".env",
        ]
        for path in search_paths:
            if path.exists():
                return path
        return None

    def _load(self) -> None:
        if self._loaded:
            return
        if not self._env_path or not self._env_path.exists():
            self._loaded = True
            return
        try:
            from dotenv import load_dotenv

            load_dotenv(self._env_path, override=False)
            # Also parse manually for get_secrets
            with open(self._env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        self._secrets[key.strip()] = value.strip()
            self._loaded = True
            logger.info("Loaded secrets from .env file", path=str(self._env_path))
        except ImportError:
            logger.warning("python-dotenv not installed, skipping .env file")
            self._loaded = True
        except Exception as exc:
            logger.error("Failed to load .env file", path=str(self._env_path), error=str(exc))
            self._loaded = True

    @property
    def name(self) -> str:
        return "dotenv"

    @property
    def is_available(self) -> bool:
        return self._env_path is not None and self._env_path.exists()

    def get_secret(self, key: str) -> str | None:
        self._load()
        # Check parsed secrets first, then environment (which dotenv may have set)
        return self._secrets.get(key) or os.environ.get(key)

    def get_secrets(self, prefix: str = "") -> dict[str, str]:
        self._load()
        if prefix:
            return {k: v for k, v in self._secrets.items() if k.startswith(prefix)}
        return dict(self._secrets)


# ─── HashiCorp Vault Backend ──────────────────────────────────────────────────


class VaultBackend(SecretBackend):
    """HashiCorp Vault backend using hvac."""

    def __init__(
        self,
        url: str | None = None,
        token: str | None = None,
        mount_point: str = "secret",
        namespace: str | None = None,
    ):
        self._url = url or os.environ.get("VAULT_ADDR", "http://localhost:8200")
        self._token = token or os.environ.get("VAULT_TOKEN")
        self._mount_point = mount_point
        self._namespace = namespace or os.environ.get("VAULT_NAMESPACE")
        self._client: Any | None = None
        self._initialized = False

    def _initialize(self) -> bool:
        if self._initialized:
            return self._client is not None
        if not self._token:
            logger.debug("Vault token not configured")
            self._initialized = True
            return False
        try:
            import hvac

            self._client = hvac.Client(
                url=self._url,
                token=self._token,
                namespace=self._namespace,
            )
            if not self._client.is_authenticated():
                logger.warning("Vault authentication failed")
                self._client = None
                self._initialized = True
                return False
            logger.info("Vault client initialized", url=self._url, mount=self._mount_point)
            self._initialized = True
            return True
        except ImportError:
            logger.warning("hvac not installed, Vault backend unavailable")
            self._initialized = True
            return False
        except Exception as exc:
            logger.error("Failed to initialize Vault client", error=str(exc))
            self._initialized = True
            return False

    @property
    def name(self) -> str:
        return "vault"

    @property
    def is_available(self) -> bool:
        return self._initialize()

    def get_secret(self, key: str) -> str | None:
        if not self._initialize() or not self._client:
            return None
        try:
            # Try KV v2 first
            secret_path = f"{self._mount_point}/data/{key}"
            response = self._client.secrets.kv.v2.read_secret_version(
                path=key, mount_point=self._mount_point
            )
            if response and "data" in response and "data" in response["data"]:
                data = response["data"]["data"]
                # Return the first value or the whole JSON
                if len(data) == 1:
                    return next(iter(data.values()))
                return json.dumps(data)
        except Exception as e:
            logging.warning(f"Failed to read secret from KV v2: {e}")
        try:
            # Try KV v1
            response = self._client.secrets.kv.v1.read_secret(
                path=key, mount_point=self._mount_point
            )
            if response and "data" in response:
                data = response["data"]
                if len(data) == 1:
                    return next(iter(data.values()))
                return json.dumps(data)
        except Exception as exc:
            logger.debug("Vault secret not found", key=key, error=str(exc))
        return None

    def get_secrets(self, prefix: str = "") -> dict[str, str]:
        if not self._initialize() or not self._client:
            return {}
        secrets = {}
        try:
            # List secrets at mount point
            list_response = self._client.secrets.kv.v2.list_secrets(
                path=prefix, mount_point=self._mount_point
            )
            if list_response and "data" in list_response and "keys" in list_response["data"]:
                for key in list_response["data"]["keys"]:
                    full_key = f"{prefix}{key}".rstrip("/")
                    value = self.get_secret(full_key)
                    if value:
                        secrets[full_key] = value
        except Exception as exc:
            logger.debug("Failed to list Vault secrets", prefix=prefix, error=str(exc))
        return secrets


# ─── SOPS/Age Encrypted File Backend ──────────────────────────────────────────


class SopsBackend(SecretBackend):
    """Loads secrets from SOPS-encrypted files (supports age, PGP, KMS)."""

    def __init__(self, secrets_dir: Path | None = None):
        self._secrets_dir = secrets_dir or Path.cwd() / "secrets"
        self._cache: dict[str, str] = {}
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        if not self._secrets_dir.exists():
            self._loaded = True
            return
        try:
            for secret_file in self._secrets_dir.glob("*.enc.*"):
                if secret_file.suffix in (".yaml", ".yml", ".json", ".env"):
                    decrypted = self._decrypt_file(secret_file)
                    if decrypted:
                        self._cache.update(decrypted)
            self._loaded = True
            logger.info(
                "Loaded secrets from SOPS files", dir=str(self._secrets_dir), count=len(self._cache)
            )
        except Exception as exc:
            logger.error("Failed to load SOPS secrets", dir=str(self._secrets_dir), error=str(exc))
            self._loaded = True

    def _decrypt_file(self, file_path: Path) -> dict[str, str]:
        """Decrypt a SOPS file and return parsed secrets."""
        try:
            # Use sops command line tool
            result = subprocess.run(
                ["sops", "-d", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.warning("SOPS decryption failed", file=str(file_path), error=result.stderr)
                return {}

            content = result.stdout.strip()
            if file_path.suffix in (".yaml", ".yml"):
                import yaml

                data = yaml.safe_load(content)
            elif file_path.suffix == ".json":
                data = json.loads(content)
            elif file_path.suffix == ".env":
                data = {}
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        data[key.strip()] = value.strip()
            else:
                return {}

            # Flatten nested dicts with prefix
            return self._flatten_dict(data, prefix=file_path.stem.replace(".enc", "") + "_")
        except Exception as exc:
            logger.warning("Failed to parse SOPS file", file=str(file_path), error=str(exc))
            return {}

    def _flatten_dict(self, data: dict, prefix: str = "") -> dict[str, str]:
        """Flatten nested dictionary with prefix."""
        result = {}
        for key, value in data.items():
            full_key = f"{prefix}{key}".upper()
            if isinstance(value, dict):
                result.update(self._flatten_dict(value, f"{full_key}_"))
            else:
                result[full_key] = str(value)
        return result

    @property
    def name(self) -> str:
        return "sops"

    @property
    def is_available(self) -> bool:
        return self._secrets_dir.exists() and any(self._secrets_dir.glob("*.enc.*"))

    def get_secret(self, key: str) -> str | None:
        self._load()
        # Try exact match first
        if key in self._cache:
            return self._cache[key]
        # Try uppercase with common prefixes
        for prefix in ("", "TRUSTRAG_", "APP_"):
            test_key = f"{prefix}{key}".upper()
            if test_key in self._cache:
                return self._cache[test_key]
        return None

    def get_secrets(self, prefix: str = "") -> dict[str, str]:
        self._load()
        if prefix:
            prefix = prefix.upper()
            return {k: v for k, v in self._cache.items() if k.startswith(prefix)}
        return dict(self._cache)


# ─── Age-Encrypted File Backend (Simple Alternative) ──────────────────────────


class AgeBackend(SecretBackend):
    """Loads secrets from age-encrypted files (simpler than SOPS)."""

    def __init__(self, secrets_dir: Path | None = None, identity: str | None = None):
        self._secrets_dir = secrets_dir or Path.cwd() / "secrets"
        self._identity = identity or os.environ.get("AGE_IDENTITY")
        self._cache: dict[str, str] = {}
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        if not self._secrets_dir.exists():
            self._loaded = True
            return
        if not self._identity:
            logger.debug("Age identity not configured")
            self._loaded = True
            return
        try:
            for secret_file in self._secrets_dir.glob("*.age"):
                decrypted = self._decrypt_file(secret_file)
                if decrypted:
                    self._cache.update(decrypted)
            self._loaded = True
            logger.info(
                "Loaded secrets from age files", dir=str(self._secrets_dir), count=len(self._cache)
            )
        except Exception as exc:
            logger.error("Failed to load age secrets", dir=str(self._secrets_dir), error=str(exc))
            self._loaded = True

    def _decrypt_file(self, file_path: Path) -> dict[str, str]:
        """Decrypt an age file using age command line."""
        try:
            result = subprocess.run(
                ["age", "-d", "-i", self._identity, str(file_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.warning("Age decryption failed", file=str(file_path), error=result.stderr)
                return {}

            content = result.stdout.strip()
            # Parse as .env format
            data = {}
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    data[key.strip().upper()] = value.strip()
            return data
        except Exception as exc:
            logger.warning("Failed to decrypt age file", file=str(file_path), error=str(exc))
            return {}

    @property
    def name(self) -> str:
        return "age"

    @property
    def is_available(self) -> bool:
        return (
            self._secrets_dir.exists()
            and self._identity is not None
            and any(self._secrets_dir.glob("*.age"))
        )

    def get_secret(self, key: str) -> str | None:
        self._load()
        # Try exact and uppercase
        for test_key in (key, key.upper(), f"TRUSTRAG_{key}".upper()):
            if test_key in self._cache:
                return self._cache[test_key]
        return None

    def get_secrets(self, prefix: str = "") -> dict[str, str]:
        self._load()
        if prefix:
            prefix = prefix.upper()
            return {k: v for k, v in self._cache.items() if k.startswith(prefix)}
        return dict(self._cache)


# ─── Secrets Manager (Facade) ─────────────────────────────────────────────────


class SecretsManager:
    """
    Unified secrets manager with fallback chain.

    Priority order (highest first):
    1. Vault (if configured)
    2. SOPS encrypted files (if available)
    3. Age encrypted files (if available)
    4. .env file (if available)
    5. Environment variables (always available)
    """

    def __init__(self):
        self._backends: list[SecretBackend] = []
        self._initialized = False

    def initialize(self) -> None:
        """Initialize all backends in priority order."""
        if self._initialized:
            return

        settings = get_settings()

        # 1. Vault (highest priority for production)
        vault_url = getattr(settings, "vault_url", None) or os.environ.get("VAULT_ADDR")
        vault_token = getattr(settings, "vault_token", None) or os.environ.get("VAULT_TOKEN")
        if vault_url and vault_token:
            self._backends.append(VaultBackend(url=vault_url, token=vault_token))

        # 2. SOPS (for CI/CD and local encrypted files)
        sops_dir = Path(os.environ.get("SOPS_SECRETS_DIR", str(Path.cwd() / "secrets")))
        if sops_dir.exists():
            self._backends.append(SopsBackend(secrets_dir=sops_dir))

        # 3. Age (simple alternative)
        age_dir = Path(os.environ.get("AGE_SECRETS_DIR", str(Path.cwd() / "secrets")))
        age_identity = os.environ.get("AGE_IDENTITY")
        if age_dir.exists() and age_identity:
            self._backends.append(AgeBackend(secrets_dir=age_dir, identity=age_identity))

        # 4. .env file
        self._backends.append(DotEnvBackend())

        # 5. Environment variables (always last, lowest priority)
        self._backends.append(EnvBackend())

        self._initialized = True
        available = [b.name for b in self._backends if b.is_available]
        logger.info("Secrets manager initialized", available_backends=available)

    def get_secret(self, key: str, default: str | None = None) -> str | None:
        """Get a secret by key, trying backends in priority order."""
        if not self._initialized:
            self.initialize()

        for backend in self._backends:
            if backend.is_available:
                value = backend.get_secret(key)
                if value is not None:
                    logger.debug("Secret found", key=key, backend=backend.name)
                    return value

        logger.debug("Secret not found in any backend", key=key)
        return default

    def get_required_secret(self, key: str) -> str:
        """Get a secret, raising if not found."""
        value = self.get_secret(key)
        if value is None:
            raise ValueError(f"Required secret '{key}' not found in any backend")
        return value

    def get_secrets(self, prefix: str = "") -> dict[str, str]:
        """Get all secrets with optional prefix, merging from all backends."""
        if not self._initialized:
            self.initialize()

        merged: dict[str, str] = {}
        # Reverse order so higher priority backends override
        for backend in reversed(self._backends):
            if backend.is_available:
                merged.update(backend.get_secrets(prefix))
        return merged

    def get_available_backends(self) -> list[str]:
        """Get list of available backend names."""
        if not self._initialized:
            self.initialize()
        return [b.name for b in self._backends if b.is_available]


# ─── Global Instance & Convenience Functions ──────────────────────────────────


_secrets_manager: SecretsManager | None = None


def get_secrets_manager() -> SecretsManager:
    """Get the global secrets manager instance."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


def get_secret(key: str, default: str | None = None) -> str | None:
    """Convenience function to get a secret."""
    return get_secrets_manager().get_secret(key, default)


def get_required_secret(key: str) -> str:
    """Convenience function to get a required secret."""
    return get_secrets_manager().get_required_secret(key)


def load_secrets_into_env(prefix: str = "") -> int:
    """
    Load secrets into environment variables.
    Useful for libraries that only read from os.environ.
    Returns number of secrets loaded.
    """
    manager = get_secrets_manager()
    secrets = manager.get_secrets(prefix)
    count = 0
    for key, value in secrets.items():
        if key not in os.environ:
            os.environ[key] = value
            count += 1
    logger.info("Loaded secrets into environment", count=count)
    return count


# ─── Configuration Helpers ────────────────────────────────────────────────────


def configure_vault(
    url: str,
    token: str,
    mount_point: str = "secret",
    namespace: str | None = None,
) -> VaultBackend:
    """Configure and return a Vault backend."""
    return VaultBackend(url=url, token=token, mount_point=mount_point, namespace=namespace)


def configure_sops(secrets_dir: Path) -> SopsBackend:
    """Configure and return a SOPS backend."""
    return SopsBackend(secrets_dir=secrets_dir)


def configure_age(secrets_dir: Path, identity: str) -> AgeBackend:
    """Configure and return an Age backend."""
    return AgeBackend(secrets_dir=secrets_dir, identity=identity)


# ─── Secret Templates for Setup ───────────────────────────────────────────────


SOPS_CONFIG_TEMPLATE = """# .sops.yaml - SOPS configuration
# Place at repository root
creation_rules:
  - path_regex: secrets/.*\\.enc\\.(yaml|json|env)$
    age: >-
      age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    # Or use PGP:
    # pgp: "FINGERPRINT"
    # Or use KMS:
    # aws_kms: "arn:aws:kms:region:account:key/key-id"

# For age-only encryption (simpler):
# age:
#   - age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
"""

AGE_KEYGEN_HELP = """
# Generate age key pair:
# age-keygen -o age.key

# Public key (share this):
# age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
#
# Private key (keep secret, set as AGE_IDENTITY):
# AGE-SECRET-KEY-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
"""

SECRETS_DIR_STRUCTURE = """
secrets/
├── .sops.yaml           # SOPS config
├── development.enc.yaml # Encrypted dev secrets
├── staging.enc.yaml     # Encrypted staging secrets
├── production.enc.yaml  # Encrypted prod secrets
└── age.key              # Age private key (gitignored!)
"""


# ─── Example Usage ────────────────────────────────────────────────────────────

# from app.core.secrets_manager import get_secret, get_required_secret, load_secrets_into_env
#
# # Get a secret (tries Vault -> SOPS -> Age -> .env -> env vars)
# api_key = get_secret("GEMINI_API_KEY")
#
# # Get required secret (raises if not found)
# jwt_secret = get_required_secret("JWT_SECRET")
#
# # Load all secrets into os.environ for libraries that need it
# load_secrets_into_env("TRUSTRAG_")
