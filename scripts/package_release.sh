#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
# Package committed source only; never include local secrets, caches or drafts.
if [ -n "$(git status --porcelain)" ]; then
  echo "Release packaging requires a clean committed working tree." >&2
  exit 1
fi
version="$(python3 -c 'import runpy; print(runpy.run_path("apps/api/app/version.py")["STUDIO_VERSION"])')"
name="etis-engineering-studio-v${version}"
archive="$(dirname "$root")/$name.tar.gz"
if [ -e "$archive" ]; then
  echo "Archive already exists: $archive" >&2
  exit 1
fi
git archive --format=tar.gz --prefix="$name/" --output="$archive" HEAD
shasum -a 256 "$archive"
