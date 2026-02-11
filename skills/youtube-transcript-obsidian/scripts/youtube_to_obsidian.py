#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi


def hms(seconds: float) -> str:
    s = int(max(0, seconds))
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    return f"[{h:02d}:{m:02d}:{sec:02d}]"


def seconds_text(seconds: float) -> str:
    s = int(max(0, seconds or 0))
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    if h:
        return f"{h}h {m}m {sec}s"
    if m:
        return f"{m}m {sec}s"
    return f"{sec}s"


def sanitize(name: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|]", "-", name)
    return re.sub(r"\s+", " ", name).strip()[:140]


def video_id_from_url(url: str) -> str:
    patterns = [r"v=([A-Za-z0-9_-]{11})", r"youtu\.be/([A-Za-z0-9_-]{11})", r"/shorts/([A-Za-z0-9_-]{11})"]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
        return url
    raise ValueError("Cannot parse YouTube video id")


def get_metadata(url: str) -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--dump-single-json", "--no-playlist", url],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def get_transcript(video_id: str):
    api = YouTubeTranscriptApi()
    fetched = api.fetch(video_id)
    entries = []
    for item in fetched:
        entries.append({"start": float(item.start), "text": (item.text or "").strip()})
    return [e for e in entries if e["text"]]


def build_chapters(meta: dict):
    ch = meta.get("chapters") or []
    if ch:
        return [{"start": float(c.get("start_time", 0)), "title": c.get("title") or "Chapter"} for c in ch]
    return [{"start": 0.0, "title": "Transcript"}]


def chapter_for(ts: float, chapters: list) -> int:
    idx = 0
    for i, c in enumerate(chapters):
        if ts >= c["start"]:
            idx = i
        else:
            break
    return idx


def clean_multiline(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def render(meta: dict, chapters: list, transcript: list, source_url: str, vid: str, prompt_path: str) -> str:
    title = (meta.get("title") or "YouTube Transcript").strip()
    grouped = {i: [] for i in range(len(chapters))}
    for row in transcript:
        grouped[chapter_for(row["start"], chapters)].append(row)

    uploader = meta.get("uploader") or meta.get("channel") or ""
    channel_url = meta.get("channel_url") or ""
    webpage_url = meta.get("webpage_url") or source_url
    upload_date = meta.get("upload_date") or ""
    published = ""
    if len(upload_date) == 8 and upload_date.isdigit():
        published = f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
    description = clean_multiline(meta.get("description") or "")
    thumbnail = meta.get("thumbnail") or ""
    duration = meta.get("duration") or 0

    out = []
    out.append("---")
    out.append('type: "youtube-transcript"')
    out.append(f'title: "{title.replace(chr(34), chr(39))}"')
    out.append(f'video_id: "{vid}"')
    out.append(f'video_url: "{webpage_url}"')
    if uploader:
        out.append(f'channel: "{uploader.replace(chr(34), chr(39))}"')
    if channel_url:
        out.append(f'channel_url: "{channel_url}"')
    if published:
        out.append(f'published_date: "{published}"')
    out.append(f'duration_seconds: {int(duration)}')
    out.append(f'duration_text: "{seconds_text(duration)}"')
    if thumbnail:
        out.append(f'thumbnail: "{thumbnail}"')
    out.append(f'captured_at: "{datetime.now().isoformat(timespec="seconds")}"')
    out.append(f'prompt_source: "{prompt_path}"')
    out.append('tags: ["youtube", "transcript"]')
    out.append("---\n")

    out.append(f"# {title}\n")

    out.append("## Video Info")
    out.append(f"- URL: {webpage_url}")
    if uploader:
        out.append(f"- Channel: {uploader}")
    if channel_url:
        out.append(f"- Channel URL: {channel_url}")
    if published:
        out.append(f"- Published: {published}")
    out.append(f"- Duration: {seconds_text(duration)}")
    out.append("")

    out.append("## Description\n")
    out.append(description if description else "[No description]")
    out.append("")

    out.append("## Table of Contents\n")
    for c in chapters:
        out.append(f"* {hms(c['start'])} {c['title']}")

    out.append("")
    out.append("## Transcript\n")
    for i, c in enumerate(chapters):
        out.append(f"{hms(c['start'])} {c['title']}\n")
        rows = grouped.get(i, [])
        if not rows:
            out.append(f"[No transcript in this chapter] {hms(c['start'])}\n")
            out.append("")
            continue
        first = True
        for r in rows:
            text = r["text"].replace("\n", " ").strip()
            if not text:
                continue
            line = f"{text} {hms(r['start'])}"
            if first:
                line = f"Speaker 1: {line}"
                first = False
            out.append(line)
            out.append("")
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--vault", required=True)
    ap.add_argument("--out-dir", default="Inbox/YouTube Transcripts")
    ap.add_argument("--prompt", default="Inbox/Youtube Transcript prompt.md")
    args = ap.parse_args()

    vault = Path(args.vault).expanduser()
    prompt_path = vault / args.prompt
    if not prompt_path.exists():
        print(f"WARN: prompt file not found: {prompt_path}")

    meta = get_metadata(args.url)
    vid = video_id_from_url(args.url)
    transcript = get_transcript(vid)
    chapters = build_chapters(meta)
    note = render(meta, chapters, transcript, args.url, vid, args.prompt)

    out_dir = vault / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = sanitize(meta.get("title") or vid)
    out = out_dir / f"{datetime.now().strftime('%Y-%m-%d')} {fname}.md"
    out.write_text(note, encoding="utf-8")
    print(str(out))


if __name__ == "__main__":
    main()
