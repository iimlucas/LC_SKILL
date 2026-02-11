#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from shutil import which

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled


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


def get_ffmpeg_exe() -> str:
    exe = which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return ""


def asr_fallback(video_url: str):
    ffmpeg_exe = get_ffmpeg_exe()
    if not ffmpeg_exe:
        raise RuntimeError("ffmpeg not found; cannot run ASR fallback")

    env = dict(**__import__("os").environ)
    ffmpeg_dir = str(Path(ffmpeg_exe).parent)
    env["PATH"] = ffmpeg_dir + ":" + env.get("PATH", "")

    with tempfile.TemporaryDirectory(prefix="yt-asr-") as tmp:
        audio_path = f"{tmp}/audio.%(ext)s"
        ytdlp_attempts = [
            [
                sys.executable,
                "-m",
                "yt_dlp",
                "-q",
                "--extractor-args",
                "youtube:player_client=android",
                "-f",
                "bestaudio/best",
                "-o",
                audio_path,
                video_url,
            ],
            [
                sys.executable,
                "-m",
                "yt_dlp",
                "-q",
                "--cookies-from-browser",
                "chrome",
                "--extractor-args",
                "youtube:player_client=android",
                "-f",
                "bestaudio/best",
                "-o",
                audio_path,
                video_url,
            ],
            [
                sys.executable,
                "-m",
                "yt_dlp",
                "-q",
                "--cookies-from-browser",
                "safari",
                "--extractor-args",
                "youtube:player_client=android",
                "-f",
                "bestaudio/best",
                "-o",
                audio_path,
                video_url,
            ],
        ]

        last_err = None
        for cmd in ytdlp_attempts:
            try:
                subprocess.run(cmd, check=True, env=env)
                last_err = None
                break
            except subprocess.CalledProcessError as e:
                last_err = e

        if last_err is not None:
            raise RuntimeError("yt-dlp could not download audio (403/cookies issue)") from last_err

        audio_file = next(Path(tmp).glob("audio.*"), None)
        if audio_file is None:
            raise RuntimeError("failed to download audio for ASR")

        subprocess.run(
            [
                sys.executable,
                "-m",
                "whisper",
                str(audio_file),
                "--model",
                "turbo",
                "--task",
                "transcribe",
                "--output_format",
                "json",
                "--output_dir",
                tmp,
            ],
            check=True,
            env=env,
        )

        json_out = Path(tmp) / f"{audio_file.stem}.json"
        if not json_out.exists():
            raise RuntimeError("whisper did not produce json output")

        data = json.loads(json_out.read_text(encoding="utf-8"))
        segs = data.get("segments") or []
        entries = []
        for s in segs:
            text = (s.get("text") or "").strip()
            if not text:
                continue
            entries.append({"start": float(s.get("start") or 0.0), "text": text})
        return entries


def get_transcript(video_id: str, video_url: str):
    api = YouTubeTranscriptApi()
    preferred = ["en", "zh-CN", "zh", "zh-Hans", "zh-Hant"]
    fetched = None

    try:
        fetched = api.fetch(video_id, languages=preferred)
        entries = []
        for item in fetched:
            entries.append({"start": float(item.start), "text": (item.text or "").strip()})
        return [e for e in entries if e["text"]], "youtube-subtitles"
    except (NoTranscriptFound, TranscriptsDisabled):
        entries = asr_fallback(video_url)
        return [e for e in entries if e["text"]], "asr-fallback"


def build_chapters(meta: dict):
    ch = meta.get("chapters") or []
    if ch:
        return [{"start": float(c.get("start_time", 0)), "title": c.get("title") or "Chapter"} for c in ch]

    desc = (meta.get("description") or "")
    parsed = []
    for line in desc.splitlines():
        m = re.match(r"^\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*[–-]?\s*(.+?)\s*$", line)
        if not m:
            continue
        if m.group(3) is None:
            mm, ss = int(m.group(1)), int(m.group(2))
            start = mm * 60 + ss
        else:
            hh, mm, ss = int(m.group(1)), int(m.group(2)), int(m.group(3))
            start = hh * 3600 + mm * 60 + ss
        title = m.group(4).strip()
        if title:
            parsed.append({"start": float(start), "title": title})
    if parsed:
        return parsed

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


def sentence_count(text: str) -> int:
    parts = re.split(r"(?<=[.!?。！？])\s+", text.strip())
    parts = [p for p in parts if p.strip()]
    return max(1, len(parts))


def is_non_speech(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if re.fullmatch(r"[\[(（【].*[\])）】]", t):
        return True
    low = t.lower()
    markers = ["laughter", "music", "applause", "laughs", "[音乐", "[笑", "（笑", "【音乐", "【笑"]
    return any(m in low for m in markers)


def clean_caption_text(text: str) -> str:
    t = text.strip()
    t = re.sub(r"^>+\s*", "", t)
    t = re.sub(r"\s+", " ", t)
    t = t.replace("[", "").replace("]", "")
    return t.strip()


def flush_paragraph(out: list, speaker: str, buf: list, last_ts: float, labeled: bool) -> bool:
    if not buf:
        return labeled
    text = " ".join(buf).strip()
    line = f"{text} {hms(last_ts)}"
    if not labeled:
        line = f"{speaker}: {line}"
        labeled = True
    out.append(line)
    out.append("")
    buf.clear()
    return labeled


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
    out.append(title)
    out.append("")
    out.append("Table of Contents")
    out.append("")
    for c in chapters:
        out.append(f"* {hms(c['start'])} {c['title']}")

    out.append("")
    for i, c in enumerate(chapters):
        out.append(f"{hms(c['start'])} {c['title']}")
        out.append("")
        rows = grouped.get(i, [])
        if not rows:
            out.append(f"[No transcript in this chapter] {hms(c['start'])}\n")
            out.append("")
            continue

        speaker = uploader if uploader else "Speaker 1"
        labeled = False
        buf = []
        buf_sentences = 0
        last_ts = c["start"]

        for r in rows:
            text = clean_caption_text(r["text"].replace("\n", " "))
            if not text:
                continue

            if is_non_speech(text):
                labeled = flush_paragraph(out, speaker, buf, last_ts, labeled)
                event = text
                if not (event.startswith("[") and event.endswith("]")):
                    event = f"[{event}]"
                out.append(f"{event} {hms(r['start'])}")
                out.append("")
                continue

            buf.append(text)
            buf_sentences += sentence_count(text)
            last_ts = r["start"]

            # Dialogue paragraphs: roughly 2-4 sentences per paragraph
            if buf_sentences >= 3:
                labeled = flush_paragraph(out, speaker, buf, last_ts, labeled)
                buf_sentences = 0

        labeled = flush_paragraph(out, speaker, buf, last_ts, labeled)
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def transcript_as_lines(transcript: list) -> str:
    lines = []
    for r in transcript:
        text = clean_caption_text((r.get("text") or "").replace("\n", " "))
        if not text:
            continue
        lines.append(f"{hms(float(r.get('start', 0)))} {text}")
    return "\n".join(lines)


def render_with_gemini(meta: dict, chapters: list, transcript: list, source_url: str, prompt_text: str, transcript_source: str) -> str:
    if which("gemini") is None:
        raise RuntimeError("gemini CLI not found")

    title = (meta.get("title") or "YouTube Transcript").strip()
    uploader = meta.get("uploader") or meta.get("channel") or "Speaker 1"
    chapter_text = "\n".join([f"- {hms(c['start'])} {c['title']}" for c in chapters])
    transcript_lines = transcript_as_lines(transcript)

    instruction = f"""
You must strictly follow the following prompt spec when formatting output.

--- SPEC START ---
{prompt_text.strip()}
--- SPEC END ---

Now produce final transcript for this video:
- Title: {title}
- URL: {source_url}
- Speaker hint: {uploader}
- Transcript source: {transcript_source}

Detected chapters:
{chapter_text}

Raw transcript lines (verbatim, do not translate):
{transcript_lines}

Hard constraints:
1) Output only the final formatted transcript body. No extra commentary.
2) Keep transcript language exactly as source transcript.
3) Timestamp format must be [HH:MM:SS] everywhere.
4) Include title line, then Table of Contents, then full chapter-segmented transcript.
5) Follow Dialogue Paragraphs rule in the spec exactly.
""".strip()

    proc = subprocess.run(["gemini", instruction], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "gemini command failed")
    output = (proc.stdout or "").strip()
    if not output:
        raise RuntimeError("gemini returned empty output")
    return output + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--vault", required=True)
    ap.add_argument("--out-dir", default="Inbox/YouTube Transcripts")
    ap.add_argument("--prompt", default="Inbox/Youtube Transcript prompt.md")
    args = ap.parse_args()

    vault = Path(args.vault).expanduser()
    prompt_path = vault / args.prompt
    prompt_text = ""
    if prompt_path.exists():
        prompt_text = prompt_path.read_text(encoding="utf-8")
    else:
        print(f"WARN: prompt file not found: {prompt_path}")

    meta = get_metadata(args.url)
    vid = video_id_from_url(args.url)
    transcript, transcript_source = get_transcript(vid, args.url)
    chapters = build_chapters(meta)

    try:
        if prompt_text:
            note = render_with_gemini(meta, chapters, transcript, args.url, prompt_text, transcript_source)
        else:
            note = render(meta, chapters, transcript, args.url, vid, args.prompt)
    except Exception as e:
        print(f"WARN: gemini formatting failed, fallback to local renderer: {e}")
        note = render(meta, chapters, transcript, args.url, vid, args.prompt)

    if transcript_source == "asr-fallback":
        note = note.rstrip() + "\n\nsource: asr-fallback\n"

    out_dir = vault / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = sanitize(meta.get("title") or vid)
    out = out_dir / f"{datetime.now().strftime('%Y-%m-%d')} {fname}.md"
    out.write_text(note, encoding="utf-8")
    print(str(out))


if __name__ == "__main__":
    main()
