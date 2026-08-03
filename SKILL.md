---
name: youtube-fetcher
description: >-
  Turn a YouTube video into a structured, Obsidian-ready archival Markdown note
  containing its transcript, creator metadata, description, chapters, language,
  and capture provenance. Use when a user shares a YouTube URL or video ID and
  wants transcripts, captions, subtitles, notes, a knowledge-base record,
  summarization, analysis of what was said, or YouTube content saved to Markdown.
  When a user pastes only a YouTube link, fetch the note and report where it was
  saved.
---

# YouTube Fetcher

Turn one YouTube link into one queryable Markdown knowledge note. The bundled
script uses `youtube-transcript-api` for captions, optionally uses `yt-dlp` for
richer metadata, and needs no API key.

## Workflow

1. Resolve `scripts/fetch_transcript.py` relative to this `SKILL.md`. Do not
   assume a particular Codex, Claude, Skillshare, or home-directory install path.
2. If the request is only a YouTube link, run the script with its defaults.
3. Use `--stdout` when the user wants the transcript in the conversation rather
   than a saved note.
4. Use `--output-dir` when the user names an Obsidian vault or notes directory.
   A specific `--output` file takes precedence.
5. Report the saved path and any language-fallback warning. Read the result only
   when the user also wants a summary, analysis, or follow-up work.

Typical invocation, where `SKILL_DIR` is the directory containing this file:

```bash
python3 "$SKILL_DIR/scripts/fetch_transcript.py" "https://youtu.be/VIDEO_ID"
```

## Safe Agent Behavior

- Run without `--force` first. Exit code `3` means an existing note was found
  and left unchanged; report that outcome and ask before overwriting.
- Never install Python packages, Homebrew packages, or `yt-dlp` automatically.
  If exit code `2` reports a missing required dependency, show the user the
  suggested command and ask for permission before changing their system.
- Do not claim the requested language was used when the script reports a
  fallback. The saved note records the actual selected caption language.
- Do not silently change the output directory. The precedence is:
  `--output`, then `--output-dir`, then `YOUTUBE_FETCHER_DIR`, then
  `~/yt_transcripts/`.

## Useful Options

```bash
# Put notes in an Obsidian vault or another directory
python3 "$SKILL_DIR/scripts/fetch_transcript.py" URL --output-dir ~/Notes/Vault

# Save to one exact file
python3 "$SKILL_DIR/scripts/fetch_transcript.py" URL --output ~/Notes/video.md

# Print Markdown instead of saving it
python3 "$SKILL_DIR/scripts/fetch_transcript.py" URL --stdout

# Request captions in a language, with truthful English fallback
python3 "$SKILL_DIR/scripts/fetch_transcript.py" URL --lang es

# Include timestamps or export raw JSON/SRT
python3 "$SKILL_DIR/scripts/fetch_transcript.py" URL --timestamps
python3 "$SKILL_DIR/scripts/fetch_transcript.py" URL --format json
python3 "$SKILL_DIR/scripts/fetch_transcript.py" URL --format srt

# Inspect available caption languages or dependencies
python3 "$SKILL_DIR/scripts/fetch_transcript.py" URL --list
python3 "$SKILL_DIR/scripts/fetch_transcript.py" --check-deps
```

Other useful flags are `--source`, `--no-description`, and `--force`.

## Capabilities and Boundaries

- **Network:** contacts YouTube caption endpoints and the YouTube oEmbed API.
  When available, `yt-dlp` contacts YouTube for descriptions, chapters, upload
  dates, and duration.
- **Filesystem:** reads only existing Markdown notes in the resolved output
  directory for duplicate detection and writes the requested Markdown, JSON, or
  SRT result there.
- **Subprocess:** invokes the locally installed `yt-dlp` executable for metadata.
- **Dependencies:** requires `youtube-transcript-api` and `requests`; `yt-dlp` is
  optional. The script reports missing dependencies but does not install them.
- **Limits:** requires captions that YouTube makes accessible. It does not
  download video, run Whisper, identify speakers, or translate captions.

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Invalid input or fetch failure |
| `2` | Missing required dependency |
| `3` | Existing note preserved; overwrite not approved |
