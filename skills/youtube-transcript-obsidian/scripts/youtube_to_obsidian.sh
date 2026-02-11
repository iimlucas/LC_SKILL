#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VAULT="$HOME/Documents/ObsidianVault"
OUT_DIR="Inbox/YouTube Transcripts"
PROMPT_REL="Inbox/Youtube Transcript prompt.md"

usage() {
  cat <<'EOF'
Usage:
  youtube_to_obsidian.sh [--vault <vault_path>] [--out-dir <vault_relative_dir>] [--prompt <vault_relative_prompt>] <youtube_url>
EOF
}

URL=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --vault)
      VAULT="${2:-}"; shift 2 ;;
    --out-dir)
      OUT_DIR="${2:-}"; shift 2 ;;
    --prompt)
      PROMPT_REL="${2:-}"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      URL="$1"; shift ;;
  esac
done

if [[ -z "$URL" ]]; then
  usage
  exit 1
fi

python3 -m pip install --user -q yt-dlp youtube-transcript-api

python3 "$SCRIPT_DIR/youtube_to_obsidian.py" \
  --url "$URL" \
  --vault "$VAULT" \
  --out-dir "$OUT_DIR" \
  --prompt "$PROMPT_REL"
