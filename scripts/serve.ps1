#requires -Version 5.1
<#
.SYNOPSIS
    Windows entry point for the TRUSTRAG local stack.

.DESCRIPTION
    Thin wrapper around scripts/serve.py. The Python script owns all logic and
    reads every port from config/ports.yaml; this file only finds an interpreter
    and forwards arguments, so behaviour stays identical on macOS, Linux and
    Windows.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\serve.ps1 doctor
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\serve.ps1 serve -Detach
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\serve.ps1 stop
#>
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$entry = Join-Path $root 'scripts\serve.py'

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    & $python.Source $entry @Rest
} else {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if (-not $launcher) {
        throw 'Python 3.11+ is required. Install it from https://www.python.org/downloads/ and enable "Add Python to PATH".'
    }
    & $launcher.Source -3 $entry @Rest
}

exit $LASTEXITCODE
