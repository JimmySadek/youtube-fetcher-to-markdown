---
name: youtube-fetcher
description: Fetch transcripts from YouTube videos and save as structured Markdown files to ~/yt_transcripts/. Activates when the user wants to get captions, subtitles, or transcripts from YouTube videos for note-taking, summarization, or analysis.
---

# YouTube Fetcher

## Overview

Fetches transcripts from YouTube videos and saves them as structured Markdown files with YAML frontmatter. Uses two tools:
- **yt-dlp** — video metadata (title, channel, description, duration, chapters)
- **youtube-transcript-api** — transcript/captions extraction

Each file includes full video metadata, the video description (with links and chapters), and the transcript. Files are saved to `~/yt_transcripts/` with the naming convention `YYYY-MM-DD_video-title-slug.md`.

## When to Use This Skill

- User shares a YouTube URL and wants the transcript
- Keywords: "transcript", "captions", "subtitles", "YouTube", "video text"
- Note-taking workflows that reference YouTube content
- Summarization tasks starting from a YouTube video

## Prerequisites

The script checks dependencies automatically on each run and will guide you through installation if anything is missing. You can also run a manual check:

```bash
python3 .../fetch_transcript.py --check-deps
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
python3 /Users/OldJimmy/.config/skillshare/skills/youtube-fetcher/scripts/fetch_transcript.py <youtube_url_or_id>
```

This creates a file like `~/yt_transcripts/2026-03-04_video-title-here.md`.

### Duplicate Detection

If a video was already transcribed, the script will notify you:
```
⚠ This video was already transcribed on 2026-03-04
  File: ~/yt_transcripts/2026-03-04_video-title.md

Re-transcribe anyway? [y/N]:
```

Use `--force` to skip the duplicate check.

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
| 3 | Duplicate skipped (user declined re-fetch) |

## Output Structure

### File Location
`~/yt_transcripts/YYYY-MM-DD_video-title-slugified.md`

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
