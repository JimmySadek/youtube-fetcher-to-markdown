# YouTube Fetcher to Markdown

<p align="center">
  <img src="assets/banner.png" alt="YouTube Fetcher to Markdown — Claude Code Skill" width="100%">
</p>

YouTube video in, structured Markdown note out. Title, channel, description, chapters, transcript, and YAML frontmatter — one command, no API keys.

```bash
npx skills add JimmySadek/youtube-fetcher-to-markdown
```

## What you get

Paste a YouTube link, get a file like this:

```
~/yt_transcripts/2026-03-04_obsidian-the-king-of-learning-tools_[hSTy_BInQs8].md
```

```markdown
---
title: "Obsidian: The King of Learning Tools (FULL GUIDE + SETUP)"
channel: "Odysseas"
url: "https://www.youtube.com/watch?v=hSTy_BInQs8"
video_id: "hSTy_BInQs8"
fetched: "2026-03-04"
source_project: "my-project"
language: "en"
caption_type: "manual"
duration: "36m 26s"
upload_date: "2024-04-24"
tags:
  - yt-transcript
---

# Obsidian: The King of Learning Tools (FULL GUIDE + SETUP)

## Video Details
| Field    | Value |
|----------|-------|
| URL      | https://www.youtube.com/watch?v=hSTy_BInQs8 |
| Channel  | Odysseas |
| Duration | 36m 26s |
| Uploaded | 2024-04-24 |
| Fetched  | 2026-03-04 |
| Source   | my-project |
| Language | en (manual) |

## Video Description
Obsidian has been the centerpiece of my self-education...
[Full description with links and resources]

### Chapters
- `00:00` Intro
- `00:16` Avoiding Toxic Perfectionism
- `02:23` My Testimony
- ...

## Transcript
almost a year ago I started building this you can call it
a personal network of knowledge but you might know it as a...
```

The YAML frontmatter means tools like [Dataview](https://github.com/blacksmithgu/obsidian-dataview) can query across your whole transcript collection — filter by channel, date, language, whatever you need.

## Why this exists

There are dozens of transcript extractors. They give you raw caption text and nothing else.

If you're building a knowledge base in Obsidian, Logseq, or plain Markdown, you need more than captions. You need to know what video this came from, who made it, when you captured it, and the creator's own description with chapter breakdowns and links.

This skill captures all of that in one command, no API keys required.

## Features

### What it captures
- Transcript text (manual and auto-generated captions)
- Video metadata: title, channel, duration, upload date
- The creator's description with links and resources
- Chapter markers with timestamps

### How it saves
- Markdown files with YAML frontmatter — queryable with Obsidian Dataview
- Filenames include the date, title slug, and video ID for easy lookup
- Output also available as JSON or SRT

### Things that save you time
- Duplicate detection — warns you if a video was already transcribed
- Source tracking — records which project directory triggered the fetch
- Auto-checks dependencies on startup and tells you what to install
- Still works without `yt-dlp` (you lose description and chapters, but keep the transcript)

## How it works

```
YouTube URL → yt-dlp (metadata) + youtube-transcript-api (captions) → Structured Markdown
```

The script extracts the video ID from whatever URL format you give it, checks for duplicates, pulls metadata from `yt-dlp` and captions from `youtube-transcript-api`, combines them into a single Markdown file with frontmatter, and saves it to `~/yt_transcripts/`.

If `yt-dlp` isn't installed, it falls back to YouTube's oEmbed API for basic metadata (title and channel) and still fetches the transcript.

## Installation

### Install the skill

```bash
npx skills add JimmySadek/youtube-fetcher-to-markdown
```

Or clone manually:

```bash
git clone https://github.com/JimmySadek/youtube-fetcher-to-markdown.git ~/.config/skillshare/skills/youtube-fetcher
```

### Install dependencies

```bash
pip install youtube-transcript-api requests
brew install yt-dlp  # macOS — or: pip install yt-dlp
```

`yt-dlp` is optional but recommended. Without it, you still get the transcript but lose the video description, chapters, and duration.

### Verify

```bash
python3 ~/.config/skillshare/skills/youtube-fetcher/scripts/fetch_transcript.py --check-deps
```

## Usage

Easiest way — just tell Claude:

> "Get me the transcript for https://youtu.be/hSTy_BInQs8"

Claude runs the skill, saves the file, and tells you where it went. That's it.

### Running it manually

```bash
python3 ~/.config/skillshare/skills/youtube-fetcher/scripts/fetch_transcript.py "https://youtu.be/VIDEO_ID"
```

### Options

| Flag | What it does |
|------|-------------|
| `--timestamps` / `-t` | Add `[MM:SS]` timestamps to each line of the transcript |
| `--lang` / `-l` | Fetch captions in a specific language (default: `en`) |
| `--source` / `-s` | Override the source project name in metadata |
| `--output` / `-o` | Save to a custom file path instead of `~/yt_transcripts/` |
| `--format` / `-f` | Output as `json` or `srt` instead of Markdown |
| `--force` | Skip duplicate check, always re-fetch |
| `--no-description` | Skip the video description section |
| `--stdout` | Print to terminal instead of saving to a file |
| `--list` | Show available transcript languages for a video |
| `--check-deps` | Check that all dependencies are installed |

### Examples

```bash
# Transcript with timestamps
python3 .../fetch_transcript.py "https://youtu.be/hSTy_BInQs8" --timestamps

# Fetch Spanish captions
python3 .../fetch_transcript.py "https://youtu.be/hSTy_BInQs8" --lang es

# Export as SRT subtitle file
python3 .../fetch_transcript.py "https://youtu.be/hSTy_BInQs8" --format srt

# Re-fetch a video you've already transcribed
python3 .../fetch_transcript.py "https://youtu.be/hSTy_BInQs8" --force
```

## Compatibility

Works with any agent that supports the SKILL.md format:

| Agent | Install |
|-------|---------|
| Claude Code | `npx skills add JimmySadek/youtube-fetcher-to-markdown` |
| Cursor, Windsurf, Gemini CLI, Codex | Same command |
| Any other agent | Clone the repo, point your agent at `SKILL.md` |

## Requirements

| Dependency | Required? | What it does |
|-----------|-----------|-------------|
| Python 3.8+ | Yes | Runs the script |
| `youtube-transcript-api` | Yes | Pulls captions from YouTube |
| `requests` | Yes | Fallback metadata via YouTube's oEmbed API |
| `yt-dlp` | Recommended | Gets video description, chapters, and duration |

## Limitations

- Only works on videos that have captions (manual or auto-generated). For videos with no captions at all, use [Whisper](https://github.com/openai/whisper).
- Some uploaders disable captions on their videos.
- Private or age-restricted videos may not be accessible.

<details>
<summary>Exit codes (for debugging)</summary>

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Runtime error (fetch failed, invalid URL) |
| `2` | Missing required dependencies |
| `3` | Duplicate skipped (video already transcribed) |

</details>

## License

MIT
