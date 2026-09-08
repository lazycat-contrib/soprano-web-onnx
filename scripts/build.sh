#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${GITHUB_ACTIONS:-}" != true ]]; then
  echo 'Release downloads and LPK preparation run only in GitHub Actions.' >&2
  exit 1
fi
npm ci --ignore-scripts --omit=optional --no-audit --no-fund
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
commit=$(python3 -c 'import json; print(json.load(open("upstream.json"))["commit"])')
[[ "$commit" =~ ^[0-9a-f]{40}$ ]]
# The immutable commit behind the selected Release's Source code archive.
curl --fail --location --retry 3 "https://codeload.github.com/KevinAHM/soprano-web-onnx/tar.gz/$commit" -o "$work/source.tar.gz"
mkdir "$work/source"
tar -xzf "$work/source.tar.gz" --strip-components=1 -C "$work/source"
python3 scripts/prepare.py "$work/source"
node scripts/smoke.cjs
