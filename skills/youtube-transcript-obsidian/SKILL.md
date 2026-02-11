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

## Default models / methods

- Transcript source (priority):
  1. `youtube-subtitles` (youtube-transcript-api)
  2. `asr-fallback` (Whisper, when subtitles are unavailable/disabled)
- Restructure model: `gemini-3-pro` (via Gemini CLI)

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
  --gemini-model "gemini-3-pro" \
  "<youtube_url>"
```

ASR test mode (force Whisper even when subtitles exist):

```bash
bash scripts/youtube_to_obsidian.sh --force-asr "<youtube_url>"
```

## What it does

1. Fetch video metadata via `yt-dlp`.
2. Try subtitles via `youtube-transcript-api`.
3. If subtitles fail/disabled, use Whisper ASR fallback.
4. Send prompt + chapters + raw transcript lines to Gemini CLI for strict prompt-based restructuring.
5. Save the note into your Obsidian vault.
6. Append run metadata at the end of note:
   - `transcription_method: ...`
   - `restructure_model: ...`

## Notes

- Chapters use YouTube metadata first, then attempt parsing from description timestamps.
- Output format is driven by `Inbox/Youtube Transcript prompt.md` when present.
- If Gemini formatting fails, script falls back to local renderer.
