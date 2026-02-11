---
name: xiaoyuzhou-dl
description: Download Xiaoyuzhou (小宇宙) podcast episodes (audio + markdown show notes) using the GitHub project slarkio/xyz-dl. Use when the user asks to download a single episode, batch-download by links/IDs, or set a default output folder for Xiaoyuzhou content.
---

# Xiaoyuzhou Downloader

Use `scripts/download_xiaoyuzhou.sh` for deterministic downloads.

## Workflow

1. Run the script with one episode URL/ID (or multiple).
2. Default output dir: `~/Downloads/Podcast/xiaoyuzhou`.
3. Return saved file paths to the user.
4. If user asks to upload/share, create a gist with `gh gist create <file>`.

## Commands

```bash
# single episode (audio + md)
bash scripts/download_xiaoyuzhou.sh "https://www.xiaoyuzhoufm.com/episode/<episode_id>"

# only audio
bash scripts/download_xiaoyuzhou.sh --mode audio "<episode_url_or_id>"

# custom output dir
bash scripts/download_xiaoyuzhou.sh --output "/path/to/dir" "<episode_url_or_id>"

# multiple episodes
bash scripts/download_xiaoyuzhou.sh "<id_or_url_1>" "<id_or_url_2>"
```

## Notes

- Under the hood this skill uses: `https://github.com/slarkio/xyz-dl`.
- If `uv` is missing, the script installs it via `pip3 install --user uv`.
- If `tools/xyz-dl` exists, script updates it with `git pull`; otherwise it clones.
- Respect copyright; downloaded content is for personal use.
