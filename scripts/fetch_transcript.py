#!/usr/bin/env python3
"""Fetch YouTube video transcripts and save as structured Markdown files.

Uses yt-dlp for video metadata (title, channel, description, duration, chapters)
and youtube-transcript-api for the actual transcript/captions.

Exit codes:
    0 - Success
    1 - Runtime error (fetch failed, invalid URL, etc.)
    2 - Missing dependencies
    3 - Duplicate skipped (video already transcribed, user declined re-fetch)
"""

import argparse
import importlib
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

# ── Exit codes ──────────────────────────────────────────────────────────────
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_MISSING_DEPS = 2
EXIT_DUPLICATE_SKIPPED = 3

TRANSCRIPTS_DIR = Path.home() / "yt_transcripts"


# ── Dependency checks ──────────────────────────────────────────────────────
def check_dependencies() -> list[dict]:
    """Check all required dependencies and return a list of missing ones."""
    missing = []

    # Python packages
    python_deps = [
        {
            "module": "youtube_transcript_api",
            "name": "youtube-transcript-api",
            "install": "pip install youtube-transcript-api",
        },
        {
            "module": "requests",
            "name": "requests",
            "install": "pip install requests",
        },
    ]
    for dep in python_deps:
        try:
            importlib.import_module(dep["module"])
        except ImportError:
            missing.append({
                "name": dep["name"],
                "type": "python",
                "install": dep["install"],
            })

    # System binaries
    if not shutil.which("yt-dlp"):
        missing.append({
            "name": "yt-dlp",
            "type": "system",
            "install": "brew install yt-dlp  # or: pip install yt-dlp",
            "optional": True,
        })

    return missing


def print_dependency_report(missing: list[dict]) -> None:
    """Print a clear, actionable dependency report."""
    required = [d for d in missing if not d.get("optional")]
    optional = [d for d in missing if d.get("optional")]

    if required:
        print("\n╔══════════════════════════════════════════════════╗", file=sys.stderr)
        print("║       Missing Required Dependencies              ║", file=sys.stderr)
        print("╚══════════════════════════════════════════════════╝\n", file=sys.stderr)
        for dep in required:
            print(f"  ✗ {dep['name']}", file=sys.stderr)
            print(f"    Install: {dep['install']}\n", file=sys.stderr)
        print("  ── Quick install all ──", file=sys.stderr)
        installs = " ".join(d["name"] for d in required if d["type"] == "python")
        if installs:
            print(f"  pip install {installs}\n", file=sys.stderr)

    if optional:
        label = "\n" if required else ""
        print(f"{label}  ⚠ Optional (recommended):", file=sys.stderr)
        for dep in optional:
            print(f"    ○ {dep['name']} — {dep['install']}", file=sys.stderr)
            if dep["name"] == "yt-dlp":
                print("      (Without yt-dlp: no video description, chapters, or duration)\n", file=sys.stderr)


# ── Duplicate detection ────────────────────────────────────────────────────
def find_existing_transcript(video_id: str) -> Path | None:
    """Scan ~/yt_transcripts/ for an existing transcript with this video_id."""
    if not TRANSCRIPTS_DIR.exists():
        return None

    for md_file in TRANSCRIPTS_DIR.glob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            # Check YAML frontmatter for matching video_id
            if f'video_id: "{video_id}"' in content:
                return md_file
        except OSError:
            continue
    return None


def get_existing_transcript_date(filepath: Path) -> str:
    """Extract the fetched date from an existing transcript's frontmatter."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r'fetched:\s*"(\d{4}-\d{2}-\d{2})"', content)
        if match:
            return match.group(1)
    except OSError:
        pass
    return "unknown date"


# ── Core helpers ───────────────────────────────────────────────────────────
def extract_video_id(url_or_id: str) -> str:
    """Extract video ID from a YouTube URL or return as-is if already an ID."""
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    print(f"Error: Could not extract video ID from '{url_or_id}'", file=sys.stderr)
    sys.exit(EXIT_ERROR)


def slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:80]


def format_duration(seconds: int) -> str:
    """Convert seconds to human-readable duration."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m}m {s}s"
    return f"{m}m {s}s"


def fetch_video_metadata(video_id: str) -> dict:
    """Fetch full video metadata via yt-dlp (title, channel, description, etc.)."""
    if not shutil.which("yt-dlp"):
        return _fetch_metadata_oembed(video_id)

    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        result = subprocess.run(
            ["yt-dlp", "--skip-download", "--dump-json", "--no-warnings", url],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            print("Warning: yt-dlp failed, falling back to oEmbed", file=sys.stderr)
            return _fetch_metadata_oembed(video_id)

        data = json.loads(result.stdout)
        return {
            "title": data.get("title", "Untitled"),
            "channel": data.get("channel", data.get("uploader", "Unknown")),
            "description": data.get("description", ""),
            "duration": data.get("duration", 0),
            "upload_date": _format_upload_date(data.get("upload_date", "")),
            "chapters": data.get("chapters") or [],
        }
    except Exception as e:
        print(f"Warning: yt-dlp error ({e}), falling back to oEmbed", file=sys.stderr)
        return _fetch_metadata_oembed(video_id)


def _fetch_metadata_oembed(video_id: str) -> dict:
    """Fallback: fetch basic metadata via YouTube oEmbed API."""
    import requests
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return {
            "title": data.get("title", "Untitled"),
            "channel": data.get("author_name", "Unknown"),
            "description": "",
            "duration": 0,
            "upload_date": "",
            "chapters": [],
        }
    except Exception:
        return {
            "title": "Untitled", "channel": "Unknown",
            "description": "", "duration": 0,
            "upload_date": "", "chapters": [],
        }


def _format_upload_date(raw: str) -> str:
    """Convert yt-dlp date format (YYYYMMDD) to readable (YYYY-MM-DD)."""
    if raw and len(raw) == 8:
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return raw


def detect_caption_type(ytt_api, video_id: str, lang: str) -> str:
    """Detect whether the fetched transcript is manual or auto-generated."""
    try:
        transcript_list = ytt_api.list(video_id)
        for t in transcript_list:
            if t.language_code == lang or t.language_code.startswith(lang):
                return "auto-generated" if t.is_generated else "manual"
        for t in transcript_list:
            if t.language_code.startswith("en"):
                return "auto-generated" if t.is_generated else "manual"
    except Exception:
        pass
    return "unknown"


def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS or MM:SS format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def build_description_section(description: str, chapters: list) -> str:
    """Build the Video Description section from yt-dlp data."""
    if not description and not chapters:
        return ""

    parts = ["\n## Video Description\n"]

    if description:
        parts.append(description)

    if chapters:
        parts.append("\n### Chapters\n")
        for ch in chapters:
            ts = format_timestamp(ch.get("start_time", 0))
            title = ch.get("title", "")
            parts.append(f"- `{ts}` {title}")

    return "\n".join(parts)


def build_markdown(
    title: str,
    channel: str,
    video_id: str,
    fetched_date: str,
    source_project: str,
    language: str,
    caption_type: str,
    description_section: str,
    transcript_text: str,
    duration: int = 0,
    upload_date: str = "",
) -> str:
    """Build the full Markdown file content with frontmatter and transcript."""
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    # Build optional frontmatter fields
    extra_frontmatter = ""
    if duration:
        extra_frontmatter += f'\nduration: "{format_duration(duration)}"'
    if upload_date:
        extra_frontmatter += f'\nupload_date: "{upload_date}"'

    # Build optional table rows
    extra_rows = ""
    if duration:
        extra_rows += f"\n| Duration | {format_duration(duration)} |"
    if upload_date:
        extra_rows += f"\n| Uploaded | {upload_date} |"

    return f"""---
title: "{title}"
channel: "{channel}"
url: "{video_url}"
video_id: "{video_id}"
fetched: "{fetched_date}"
source_project: "{source_project}"
language: "{language}"
caption_type: "{caption_type}"{extra_frontmatter}
tags:
  - yt-transcript
---

# {title}

## Video Details

| Field    | Value |
|----------|-------|
| URL      | {video_url} |
| Channel  | {channel} |{extra_rows}
| Fetched  | {fetched_date} |
| Source   | {source_project} |
| Language | {language} ({caption_type}) |
{description_section}

## Transcript

{transcript_text}
"""


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Fetch YouTube video transcripts and save as structured Markdown",
        epilog="Exit codes: 0=success, 1=error, 2=missing deps, 3=duplicate skipped",
    )
    parser.add_argument("video", nargs="?", help="YouTube URL or video ID")
    parser.add_argument("--output", "-o", help="Custom output path (overrides ~/yt_transcripts/)")
    parser.add_argument("--timestamps", "-t", action="store_true", help="Include timestamps in transcript")
    parser.add_argument("--lang", "-l", default="en", help="Language code (default: en)")
    parser.add_argument("--format", "-f", dest="fmt", choices=["text", "json", "srt"], default="text", help="Output format (text=Markdown, json/srt=raw)")
    parser.add_argument("--list", action="store_true", help="List available transcripts")
    parser.add_argument("--source", "-s", default=None, help="Source project name (defaults to cwd name)")
    parser.add_argument("--stdout", action="store_true", help="Print to stdout instead of saving")
    parser.add_argument("--no-description", action="store_true", help="Skip video description")
    parser.add_argument("--force", action="store_true", help="Skip duplicate check, always re-fetch")
    parser.add_argument("--check-deps", action="store_true", help="Check dependencies and exit")
    args = parser.parse_args()

    # ── Dependency check ────────────────────────────────────────────────
    missing = check_dependencies()
    required_missing = [d for d in missing if not d.get("optional")]

    if args.check_deps:
        if not missing:
            print("All dependencies are installed.")
            sys.exit(EXIT_SUCCESS)
        print_dependency_report(missing)
        sys.exit(EXIT_MISSING_DEPS if required_missing else EXIT_SUCCESS)

    if required_missing:
        print_dependency_report(missing)
        sys.exit(EXIT_MISSING_DEPS)

    # Show optional warnings once (non-blocking)
    optional_missing = [d for d in missing if d.get("optional")]
    if optional_missing:
        print_dependency_report(optional_missing)

    # Now safe to import after dependency check
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.formatters import JSONFormatter, SRTFormatter

    if not args.video:
        parser.error("the following arguments are required: video")

    video_id = extract_video_id(args.video)
    ytt_api = YouTubeTranscriptApi()

    # ── List mode ───────────────────────────────────────────────────────
    if args.list:
        transcript_list = ytt_api.list(video_id)
        for t in transcript_list:
            kind = "manual" if not t.is_generated else "auto"
            print(f"  [{t.language_code}] {t.language} ({kind})")
        sys.exit(EXIT_SUCCESS)

    # ── Duplicate check ─────────────────────────────────────────────────
    if not args.force and not args.stdout and args.fmt == "text":
        existing = find_existing_transcript(video_id)
        if existing:
            fetched_on = get_existing_transcript_date(existing)
            print(f"\n  ⚠ This video was already transcribed on {fetched_on}")
            print(f"    File: {existing}\n")

            try:
                answer = input("  Re-transcribe anyway? [y/N]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = "n"

            if answer not in ("y", "yes"):
                print("  Skipped (duplicate).")
                sys.exit(EXIT_DUPLICATE_SKIPPED)
            print()

    # ── Fetch transcript ────────────────────────────────────────────────
    try:
        transcript = ytt_api.fetch(video_id, languages=[args.lang, "en"])
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    # ── Raw format outputs (json/srt) ───────────────────────────────────
    if args.fmt == "json":
        formatter = JSONFormatter()
        output = formatter.format_transcript(transcript, indent=2)
        if args.stdout:
            print(output)
        else:
            out_path = args.output or str(TRANSCRIPTS_DIR / f"{video_id}.json")
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            Path(out_path).write_text(output, encoding="utf-8")
            print(f"Saved to {out_path}")
        sys.exit(EXIT_SUCCESS)

    if args.fmt == "srt":
        formatter = SRTFormatter()
        output = formatter.format_transcript(transcript)
        if args.stdout:
            print(output)
        else:
            out_path = args.output or str(TRANSCRIPTS_DIR / f"{video_id}.srt")
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            Path(out_path).write_text(output, encoding="utf-8")
            print(f"Saved to {out_path}")
        sys.exit(EXIT_SUCCESS)

    # ── Build plain text transcript ─────────────────────────────────────
    lines = []
    for snippet in transcript:
        if args.timestamps:
            ts = format_timestamp(snippet.start)
            lines.append(f"[{ts}] {snippet.text}")
        else:
            lines.append(snippet.text)
    transcript_text = "\n".join(lines)

    # ── Fetch metadata via yt-dlp ───────────────────────────────────────
    metadata = fetch_video_metadata(video_id)
    today = date.today().isoformat()
    source_project = args.source or Path.cwd().name
    caption_type = detect_caption_type(ytt_api, video_id, args.lang)

    # ── Build description section ───────────────────────────────────────
    description_section = ""
    if not args.no_description:
        description_section = build_description_section(
            metadata["description"], metadata["chapters"]
        )

    # ── Build Markdown ──────────────────────────────────────────────────
    md_content = build_markdown(
        title=metadata["title"],
        channel=metadata["channel"],
        video_id=video_id,
        fetched_date=today,
        source_project=source_project,
        language=args.lang,
        caption_type=caption_type,
        description_section=description_section,
        transcript_text=transcript_text,
        duration=metadata["duration"],
        upload_date=metadata["upload_date"],
    )

    if args.stdout:
        print(md_content)
        sys.exit(EXIT_SUCCESS)

    # ── Save to file ────────────────────────────────────────────────────
    if args.output:
        out_path = Path(args.output)
    else:
        filename = f"{today}_{slugify(metadata['title'])}.md"
        TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = TRANSCRIPTS_DIR / filename

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md_content, encoding="utf-8")
    print(f"Saved to {out_path}")
    sys.exit(EXIT_SUCCESS)


if __name__ == "__main__":
    main()
