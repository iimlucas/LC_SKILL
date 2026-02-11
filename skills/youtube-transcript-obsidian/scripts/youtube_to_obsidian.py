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


def render(meta: dict, chapters: list, transcript: list) -> str:
    title = (meta.get("title") or "YouTube Transcript").strip()
    grouped = {i: [] for i in range(len(chapters))}
    for row in transcript:
        grouped[chapter_for(row["start"], chapters)].append(row)

    out = []
    out.append(f"# {title}\n")
    out.append("## Table of Contents\n")
    for c in chapters:
        out.append(f"* {hms(c['start'])} {c['title']}")

    out.append("")
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
    note = render(meta, chapters, transcript)

    out_dir = vault / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = sanitize(meta.get("title") or vid)
    out = out_dir / f"{datetime.now().strftime('%Y-%m-%d')} {fname}.md"
    out.write_text(note, encoding="utf-8")
    print(str(out))


if __name__ == "__main__":
    main()
