#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="/Users/luclaw/.openclaw/workspace"
REPO_DIR="$WORKSPACE/tools/xyz-dl"
DEFAULT_OUT="$HOME/Downloads/Podcast/xiaoyuzhou"
MODE="both"
OUT_DIR="$DEFAULT_OUT"

usage() {
  cat <<'EOF'
Usage:
  download_xiaoyuzhou.sh [--mode both|audio|md] [--output /path/to/dir] <episode_url_or_id> [more...]

Examples:
  download_xiaoyuzhou.sh "https://www.xiaoyuzhoufm.com/episode/69834c1bc78b823892ab6d1b"
  download_xiaoyuzhou.sh --mode audio 69834c1bc78b823892ab6d1b
  download_xiaoyuzhou.sh --output "$HOME/Downloads/Podcast/xiaoyuzhou" 69834c1bc78b823892ab6d1b
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --output|-o)
      OUT_DIR="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
    *)
      break
      ;;
  esac
done

if [[ "$MODE" != "both" && "$MODE" != "audio" && "$MODE" != "md" ]]; then
  echo "Invalid --mode: $MODE (must be both|audio|md)" >&2
  exit 1
fi

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

mkdir -p "$OUT_DIR"
mkdir -p "$WORKSPACE/tools"

if ! command -v uv >/dev/null 2>&1; then
  python3 -m pip install --user uv >/dev/null
fi

UV_BIN="$(command -v uv || true)"
if [[ -z "$UV_BIN" && -x "$HOME/Library/Python/3.9/bin/uv" ]]; then
  UV_BIN="$HOME/Library/Python/3.9/bin/uv"
fi
if [[ -z "$UV_BIN" ]]; then
  echo "uv not found after installation. Add user bin to PATH and retry." >&2
  exit 1
fi

if [[ -d "$REPO_DIR/.git" ]]; then
  git -C "$REPO_DIR" pull --ff-only >/dev/null || true
else
  git clone https://github.com/slarkio/xyz-dl.git "$REPO_DIR" >/dev/null
fi

"$UV_BIN" -q sync --directory "$REPO_DIR"

for target in "$@"; do
  "$UV_BIN" run --directory "$REPO_DIR" xyz-dl --mode "$MODE" -d "$OUT_DIR" "$target"
done

echo "Done. Files saved under: $OUT_DIR"
