"""
Script to view and purge Qdrant Cloud collections.

Usage:
  python scripts/clear_qdrant.py --list      # List all collections and point counts
  python scripts/clear_qdrant.py --purge     # Delete all collections from Qdrant Cloud
"""

import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

from qdrant_client import QdrantClient


def main():
    parser = argparse.ArgumentParser(description="Manage Qdrant Cloud collections")
    parser.add_argument("--list", action="store_true", help="List all collections")
    parser.add_argument("--purge", action="store_true", help="Delete all collections")
    args = parser.parse_args()

    url = os.environ.get("QDRANT_URL")
    api_key = os.environ.get("QDRANT_API_KEY")

    if not url:
        print("Error: QDRANT_URL environment variable is not set.")
        sys.exit(1)

    print(f"Connecting to Qdrant: {url}")
    client = QdrantClient(url=url, api_key=api_key, prefer_grpc=False, timeout=15.0)

    try:
        collections = client.get_collections().collections
    except Exception as exc:
        print(f"Failed to connect to Qdrant Cloud: {exc}")
        sys.exit(1)

    if not collections:
        print("No collections found in Qdrant Cloud. Vector database is completely clean!")
        return

    print(f"Found {len(collections)} collection(s):")
    for c in collections:
        try:
            info = client.get_collection(c.name)
            print(f"  • {c.name}: {info.points_count} points, status: {info.status}")
        except Exception:
            print(f"  • {c.name}")

    if args.purge:
        confirm = input("\nAre you sure you want to delete ALL collections above? (y/N): ")
        if confirm.lower() == "y":
            for c in collections:
                print(f"Deleting collection: {c.name}...")
                client.delete_collection(c.name)
            print("All collections successfully deleted from Qdrant Cloud!")
        else:
            print("Purge aborted.")
    elif not args.list:
        print("\nPass --purge to delete all collections, or --list to only inspect.")


if __name__ == "__main__":
    main()
