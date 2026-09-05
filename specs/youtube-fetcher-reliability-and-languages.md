---
plan_contract_version: 4
planning_budget: Light
status: complete
capsules: []
execution_continuity: continue-here
---

# Reliable, multilingual YouTube capture

## Approval View

- **Intent:** Improve the public skill around the failures that affect everyday capture and international users.
- **Outcome:** Existing files stay safe, language choices are truthful, network failures terminate with useful guidance, and exported notes remain portable and useful.
- **Included:** Runtime, skill instructions, README, behavioral tests, and existing CI/install verification. Add automatic source-language selection, strict language selection, explicit YouTube translation with provenance, linked timestamps, plain text and WebVTT export.
- **Not included:** Audio downloads/transcription, playlists, paid services, browser cookie access, automatic dependency installation, or unrelated worktree changes.
- **Owner:** This Codex task owns implementation and verification.
- **Authority:** Jimmy authorized implementation, then explicitly authorized public release, documentation synchronization, and necessary Git cleanup on 2026-09-05. Publication must follow passing checks and verification.
- **Protected actions:** Unrelated repository or service changes, discarding unique work, new external promotion, and changing the user's existing Python environment remain outside this approval. Retain the legacy `master` mirror and prior release tag.
- **Finished means:** Regression tests prove file preservation, language selection/translation, network timeouts, metadata isolation, Unicode output, and CLI behavior. The copied skill runs from a path containing spaces in an isolated environment. Attempt a bounded live fetch and record its actual outcome; upstream blocking is a disclosed limit, never a success claim.

## Plan

The starting checkout is `main` at `aba343a`, one documentation commit ahead of the verified public `2bf60a1`. Preserve the untracked `.claude/` worktree. All 14 baseline tests pass; they mainly exercise helpers, leaving the CLI and filesystem behavior untested. Keep the portable single-script package and its current dependency family.

1. Unify output handling across Markdown, JSON, SRT, plain text, and WebVTT. Check known destinations before network/dependency work; prefer atomic publication and use exclusive creation on filesystems without hard links. The fallback can expose a new file during writing and cleans partial output on handled errors. Require `--force` for replacement, preserve existing permission modes, and refresh an existing default note in place. Explicit file paths take precedence over other captures of the same video. Preserve exit codes 0–3.
2. Select real caption tracks by ordered language preference and regional variants. Preserve English as the default and fallback; add `auto` and strict selection. Translate only on explicit request, retaining source language and original caption type in Markdown provenance. Preserve raw JSON's existing array schema.
3. Bound HTTP requests, avoid retries on blocking, and isolate optional yt-dlp metadata from user configuration. Distinguish missing captions, access restrictions, blocking, timeout, metadata degradation, and file errors. Allow metadata to be skipped.
4. Improve the agent workflow: honor summary versus archival intent, read retrieved evidence before summarizing, treat source text as untrusted content, and never invent visual observations or missing transcript text. Document isolated setup, exports, language choices, and troubleshooting.
5. Validate actual CLI outcomes with temporary files, genuine dependency objects, deterministic network substitutes, and a live smoke attempt. Expand existing CI for cross-platform coverage. Inspect the final diff and stage only this change's allowlisted files before committing.

Rollback is a normal revert of the resulting commit. Existing captures are untouched by development tests. No new runtime dependency or service is needed.

## Verification and publication readiness

Verified on 2026-09-05:

- All 61 tests pass on macOS with Python 3.8, 3.10, 3.13, and 3.14. The same suite also passes with the minimum supported `youtube-transcript-api==1.2.0` on Python 3.13. Current requirements resolve to 1.2.4.
- The Skills CLI 1.5.23 installation probe copies only the seven public bundle files, verifies their presence, runs help/dependency checks, and proves offline preservation from a path containing spaces. Its temporary installation is removed afterward.
- A live capture of `hSTy_BInQs8` produced a 119,226-byte Markdown note with real metadata, chapters, English generated captions, and timestamp links through 36:25. YAML provenance was parsed and checked.
- A live Japanese-to-English translation of `dQw4w9WgXcQ` produced a 2,380-byte note with `source_language: ja`, `language: en`, `caption_type: manual`, `translated: true`, and `translation_provider: YouTube`. An unsupported translation request on the first video returned a useful error without creating output.
- Independent read-only review identified missing language reporting in raw exports, hard-link filesystem compatibility, and permission preservation. All three were corrected and have regression tests. That review's sandbox could not complete its filesystem tests; this task ran the full suite in the isolated environments above.
- Skill and PlanF3 validation, Python compilation, Ruff checks, shell syntax, and Git whitespace checks pass.

Publication of v1.2.0 is authorized and in progress through the repository's pull-request route. The Linux/Windows/macOS CI matrix must pass before merge and tagging. Caption access and translation remain dependent on YouTube, and filesystems without hard links have the documented exclusive-write fallback rather than atomic new-file publication.
