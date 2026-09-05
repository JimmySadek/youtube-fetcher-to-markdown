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
- **Included:** Runtime, skill instructions, README, behavioral tests, CI/install verification, approved public release, and cleanup of redundant repository history. Add automatic source-language selection, strict language selection, explicit YouTube translation with provenance, linked timestamps, plain text and WebVTT export.
- **Not included:** Audio downloads/transcription, playlists, paid services, browser cookie access, automatic dependency installation, or changes to unrelated repository contents.
- **Owner:** This Codex task owns implementation and verification.
- **Authority:** Jimmy authorized implementation, then explicitly authorized public release, documentation synchronization, and necessary Git cleanup on 2026-09-05. Publication must follow passing checks and verification.
- **Protected actions:** Unrelated repository or service changes, discarding unique work, new external promotion, and changing the user's existing Python environment remain outside this approval. Retain the legacy `master` mirror and prior release tag.
- **Finished means:** Regression tests prove file preservation, language selection/translation, timeouts, metadata isolation, Unicode output, and CLI behavior. Public tag, release, CI, isolated installation, and live capture agree. The canonical checkout is clean, and every retired branch or worktree has verified history/evidence custody.

## Plan

The starting checkout was `main` at `aba343a`, one documentation commit ahead of public `2bf60a1`. Implementation preserved the old `.claude/` worktree; the later approved cleanup is recorded below. The 14 baseline tests mainly exercised helpers, leaving CLI and filesystem behavior untested. The portable single-script package and dependency family are retained.

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

## Public release and final custody

[v1.2.0](https://github.com/JimmySadek/youtube-fetcher-to-markdown/releases/tag/v1.2.0)
was published on 2026-09-05 at `7401ded6c6195f38db962c95a3cc0a92a96bf42a`,
through [PR #4](https://github.com/JimmySadek/youtube-fetcher-to-markdown/pull/4).
All Linux, Windows, and macOS jobs passed in
[PR CI](https://github.com/JimmySadek/youtube-fetcher-to-markdown/actions/runs/33985647882)
and [post-merge CI](https://github.com/JimmySadek/youtube-fetcher-to-markdown/actions/runs/33985725827).
The [legacy mirror check](https://github.com/JimmySadek/youtube-fetcher-to-markdown/actions/runs/33985725846)
also passed. The release is public and is neither a draft nor a prerelease.

A fresh clone of the public tag passed all 61 tests and the Skills CLI 1.5.23
installation probe. Its live JSON capture returned 1,167 snippets (123,191 bytes),
including the end of the 36-minute video. Anonymous raw-file downloads matched
the released runtime, skill instructions, and README byte for byte.

The approved cleanup retains one active `main` worktree, the `main`/`master`
hosted branches, and both release tags. Redundant release branches and the old
worktree were retired. Historical tip `0a8d37a` is patch-equivalent and has the
same tree as canonical `2110920`; it is also preserved by a local archive ref and
a verified private Git bundle. The separate `awesome-claude-code` checkout was
moved outside skill discovery with all 780 files, byte counts, hashes, Git HEAD,
and clean status verified unchanged. Its obsolete duplicate Codex shortcut was
retired; the canonical Codex and Claude shortcuts still resolve to this repository.
Generated caches were moved recoverably; local Serena configuration was retained.
Private manifests record the exact custody paths and before/after inventory.

Caption access and translation still depend on YouTube. Filesystems without
hard links use the documented exclusive-write fallback. Historical directory
promotion and attribution work remains separate from the completed engineering
release; the v1.1 record now identifies VoltAgent's accepted submission.
