#!/usr/bin/env bash
# Run AFTER the GitHub repo Advanced3dPrinting/klipper-firmware-builder exists.
# 1) push this repo   2) trigger the first CI build on the latest Klipper tag
set -euo pipefail
PAT=$(cat /opt/data/.secrets/github/pat.txt)
REPO=Advanced3dPrinting/klipper-firmware-builder
cd "$(dirname "$0")"
git remote add origin "https://robthide37:${PAT}@github.com/${REPO}.git" 2>/dev/null || true
git push -u origin main
TAG=$(curl -sf https://api.github.com/repos/Klipper3d/klipper/releases/latest | python3 -c 'import json,sys;print(json.load(sys.stdin)["tag_name"])')
echo "latest klipper tag: $TAG"
curl -s -X POST -H "Authorization: token $PAT" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${REPO}/actions/workflows/build.yml/dispatches" \
  -d "{"ref":"main","inputs":{"klipper_ref":"${TAG}","force":"true"}}"
echo "dispatch sent — watch https://github.com/${REPO}/actions"
