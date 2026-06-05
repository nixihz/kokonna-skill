#!/usr/bin/env bash
# End-to-end: generate an image, push it to the KoKonna Frame, confirm.
#
# Usage:  KOKONNA_API_KEY=*** ./push-to-frame.sh <image-file> [name]
#         (or run `kokonna config set-key` first and omit the env var)
#
# Replace `image-gen` with whatever generator you use (DALL-E, SD, etc.).

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <image-file> [name]" >&2
  exit 1
fi

FILE="$1"
NAME="${2:-}"

echo "→ uploading $FILE"
UPLOAD_JSON=$(kokonna image upload "$FILE" ${NAME:+--name "$NAME"} --json)
echo "$UPLOAD_JSON"

ID=$(echo "$UPLOAD_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
echo "→ new image id: $ID"

echo "→ current gallery:"
kokonna image list --human
