#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
name="etis-engineering-studio-wave1"
cd "$(dirname "$root")"
tar --exclude='.venv' --exclude='node_modules' --exclude='*.db' --exclude='.git' -czf "$name.tar.gz" "$(basename "$root")"
shasum -a 256 "$name.tar.gz"
