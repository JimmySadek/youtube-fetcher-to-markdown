---
name: youtube-fetcher
description: >-
  Fetch transcripts from YouTube videos and save as structured Markdown files
  to ~/yt_transcripts/. Use this skill whenever the user shares a YouTube URL
  or video ID and wants the transcript, captions, or subtitles extracted. Also
  triggers when the user wants to take notes on a YouTube video, summarize video
  content, analyze what was said in a video, or reference YouTube content in their
  notes — even if they don't explicitly say "transcript." If the user pastes a
  YouTube link with no other context, default to fetching the transcript.
---

# YouTube Fetcher

## Overview

Fetches transcripts from YouTube videos and saves them as structured Markdown files with YAML frontmatter. Uses two tools:
- **yt-dlp** — video metadata (title, channel, description, duration, chapters)
- **youtube-transcript-api** — transcript/captions extraction

Each file includes full video metadata, the video description (with links and chapters), and the transcript. Files are saved to `~/yt_transcripts/` with the naming convention `YYYY-MM-DD_video-title-slug_[VIDEO_ID].md`.

## When to Use This Skill

- User shares a YouTube URL (any format) or video ID
- User wants a transcript, captions, subtitles, or "the text" from a video
- Note-taking or summarization workflows involving YouTube content
- User pastes a YouTube link — even without explicit instructions, default to fetching

## How Claude Should Use This Skill

The script path is: `~/.config/skillshare/skills/youtube-fetcher/scripts/fetch_transcript.py`

**Always use `--force` when running from Claude** — the duplicate check uses an interactive prompt that doesn't work in non-interactive contexts. If you need to check for duplicates first, look for matching files in `~/yt_transcripts/` yourself.

**Typical workflow:**
1. Run the script with `--force` to fetch the transcript
2. Tell the user where the file was saved
3. If the user wants a summary or analysis, read the saved file and process it

**Example invocation:**
```bash
python3 ~/.config/skillshare/skills/youtube-fetcher/scripts/fetch_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID" --force
```

**If the user wants the transcript in the conversation** (not just saved to a file), add `--stdout`:
```bash
python3 ~/.config/skillshare/skills/youtube-fetcher/scripts/fetch_transcript.py "URL" --force --stdout
```

**If deps are missing**, the script exits with code 2 and prints install instructions. Run the pip/brew commands it suggests.

## Prerequisites

The script checks dependencies automatically on each run and will guide you through installation if anything is missing. You can also run a manual check:

```bash
python3 ~/.config/skillshare/skills/youtube-fetcher/scripts/fetch_transcript.py --check-deps
```

Required:
```bash
pip install youtube-transcript-api requests
```

Recommended (for video description, chapters, duration):
```bash
brew install yt-dlp  # or: pip install yt-dlp
```

## Usage

### Default (saves structured Markdown to ~/yt_transcripts/)

```bash
python3 ~/.config/skillshare/skills/youtube-fetcher/scripts/fetch_transcript.py <youtube_url_or_id>
```

This creates a file like `~/yt_transcripts/2026-03-04_video-title-here_[dQw4w9WgXcQ].md`.

### Duplicate Detection

If a video was already transcribed, the script will:
- **Interactive terminal**: prompt `Re-transcribe anyway? [y/N]:`
- **Non-interactive** (Claude, pipes, scripts): auto-skip and suggest `--force`

Use `--force` to always re-fetch regardless of duplicates.

### Options

```bash
# With timestamps in transcript body
python3 .../fetch_transcript.py <url> --timestamps

# Specific language
python3 .../fetch_transcript.py <url> --lang es

# Override source project name
python3 .../fetch_transcript.py <url> --source "my-project"

# Custom output path
python3 .../fetch_transcript.py <url> --output ~/notes/my-transcript.md

# Skip video description (transcript only)
python3 .../fetch_transcript.py <url> --no-description

# Force re-fetch (skip duplicate check)
python3 .../fetch_transcript.py <url> --force

# Print to stdout instead of saving
python3 .../fetch_transcript.py <url> --stdout

# JSON or SRT format (raw, no Markdown wrapping)
python3 .../fetch_transcript.py <url> --format json
python3 .../fetch_transcript.py <url> --format srt

# List available transcripts for a video
python3 .../fetch_transcript.py <url> --list

# Check dependencies
python3 .../fetch_transcript.py --check-deps
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Runtime error (fetch failed, invalid URL) |
| 2 | Missing required dependencies |
| 3 | Duplicate skipped (user declined re-fetch or non-interactive) |

## Output Structure

### File Location
`~/yt_transcripts/YYYY-MM-DD_video-title-slugified_[VIDEO_ID].md`

### File Content

```markdown
---
title: "Video Title"
channel: "Channel Name"
url: "https://www.youtube.com/watch?v=VIDEO_ID"
video_id: "VIDEO_ID"
fetched: "2026-03-04"
source_project: "JARVIS-Obsidian-Setup"
language: "en"
caption_type: "manual"
duration: "36m 26s"
upload_date: "2024-01-15"
tags:
  - yt-transcript
---

# Video Title

## Video Details

| Field    | Value |
|----------|-------|
| URL      | https://www.youtube.com/watch?v=VIDEO_ID |
| Channel  | Channel Name |
| Duration | 36m 26s |
| Uploaded | 2024-01-15 |
| Fetched  | 2026-03-04 |
| Source   | JARVIS-Obsidian-Setup |
| Language | en (manual) |

## Video Description

The video description text with links, summaries, etc.

### Chapters

- `00:00` Intro
- `02:23` My Testimony
- ...

## Transcript

The full transcript text here...
```

## Accepted URL Formats

- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://youtube.com/embed/VIDEO_ID`
- Just the video ID directly

## Limitations

- Only works on videos that have captions (manual or auto-generated)
- Cannot transcribe videos without any captions — use Whisper for that
- Some videos have captions disabled by the uploader
