---
name: youtube-transcript-obsidian
description: Convert a YouTube link into a structured transcript note and save it into an Obsidian vault. Use when the user sends a YouTube URL and wants transcript text organized with title, table of contents, chapter sections, and timestamps in Obsidian.
---

# YouTube → Obsidian Transcript

Use this skill to turn a YouTube URL into a Markdown transcript note in Obsidian.

## Default paths

- Vault: `~/Documents/ObsidianVault`
- Prompt source: `Inbox/Youtube Transcript prompt.md`
- Output folder: `Inbox/YouTube Transcripts`

## Run

```bash
bash scripts/youtube_to_obsidian.sh "<youtube_url>"
```

## Options

```bash
bash scripts/youtube_to_obsidian.sh \
  --vault "~/Documents/ObsidianVault" \
  --out-dir "Inbox/YouTube Transcripts" \
  --prompt "Inbox/Youtube Transcript prompt.md" \
  "<youtube_url>"
```

## What it does

1. Fetch video metadata (title/chapters) via `yt-dlp`.
2. Fetch transcript via `youtube-transcript-api`.
3. Build Markdown with:
   - video title
   - `Table of Contents`
   - chapter headings `[HH:MM:SS] Chapter Title`
   - paragraph lines ending with `[HH:MM:SS]`
4. Save the note into your Obsidian vault.

## Notes

- Uses auto-generated captions when human captions are unavailable.
- Speaker labels are best-effort (`Speaker 1`) since YouTube captions usually do not include diarization.
- If YouTube metadata has chapter list, it is used for segmentation first.
