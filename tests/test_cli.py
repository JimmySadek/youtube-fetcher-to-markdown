"""Exercise real CLI outcomes with the caption service replaced at its boundary."""

from __future__ import annotations

import contextlib
import errno
import io
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from requests import Session, Timeout
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import RequestBlocked
from youtube_transcript_api._transcripts import (
    FetchedTranscript,
    FetchedTranscriptSnippet,
    Transcript,
    TranscriptList,
)

from test_fetch_transcript import VIDEO_ID, youtube_fetcher as app


def track(code="en", generated=False, text="Hello, world!", translations=None):
    item = Transcript(
        Session(),
        VIDEO_ID,
        "https://example.invalid/captions",
        code,
        code,
        generated,
        translations or [],
    )
    item.fetch = Mock(
        return_value=FetchedTranscript(
            [FetchedTranscriptSnippet(text, 65.25, 2.5)],
            VIDEO_ID,
            code,
            code,
            generated,
        )
    )
    return item


def tracks(*items):
    return TranscriptList(
        VIDEO_ID,
        {t.language_code: t for t in items if not t.is_generated},
        {t.language_code: t for t in items if t.is_generated},
        [],
    )


class LanguageTests(unittest.TestCase):
    def select(self, items, language, strict=False):
        with contextlib.redirect_stderr(io.StringIO()):
            return app.select_transcript(tracks(*items), language, strict)[0]

    def test_requested_generated_language_beats_manual_fallback(self):
        spanish, english = track("es", True), track("en")
        self.assertIs(self.select([english, spanish], "es"), spanish)

    def test_manual_preferred_within_same_language(self):
        manual = track("fr")
        self.assertIs(self.select([track("fr", True), manual], "fr"), manual)

    def test_regional_variant_is_retrievable(self):
        mexican = track("es-MX")
        self.assertIs(self.select([track("en"), mexican], "ES", strict=True), mexican)

    def test_exact_language_precedes_regional_variant(self):
        exact = track("es", True)
        self.assertIs(self.select([track("es-MX"), exact], "es"), exact)

    def test_ordered_preferences_precede_english(self):
        french = track("fr", True)
        self.assertIs(self.select([track("en"), french], "de, fr"), french)

    def test_strict_language_does_not_use_english(self):
        with self.assertRaisesRegex(ValueError, "Available: en"):
            self.select([track("en")], "ja", strict=True)

    def test_auto_works_without_english_and_prefers_manual(self):
        arabic = track("ar")
        self.assertIs(self.select([track("ja", True), arabic], "auto"), arabic)

    def test_auto_accepts_generated_only(self):
        japanese = track("ja", True)
        self.assertIs(self.select([japanese], "auto"), japanese)

    def test_auto_is_not_combined_with_specific_codes(self):
        with self.assertRaises(ValueError):
            self.select([track()], "auto,es")

    def test_empty_track_list_has_actionable_error(self):
        with self.assertRaisesRegex(ValueError, "Available: none"):
            self.select([], "auto")


class FileSafetyTests(unittest.TestCase):
    def test_filesystem_without_hardlinks_can_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "new.md"
            with patch.object(
                app.os, "link", side_effect=OSError(errno.ENOTSUP, "unsupported")
            ):
                app.write_output(dest, "日本語")
            self.assertEqual(dest.read_text(encoding="utf-8"), "日本語")
            self.assertEqual(list(Path(tmp).iterdir()), [dest])

    def test_fallback_preserves_a_concurrent_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "note.md"

            def competing_write(*args):
                dest.write_text("someone else's note", encoding="utf-8")
                raise OSError(errno.ENOTSUP, "unsupported")

            with patch.object(app.os, "link", side_effect=competing_write):
                with self.assertRaises(app.ExistingOutputError):
                    app.write_output(dest, "our note")
            self.assertEqual(dest.read_text(), "someone else's note")

    def test_fallback_write_failure_removes_its_partial_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "note.md"
            with contextlib.ExitStack() as stack:
                stack.enter_context(
                    patch.object(
                        app.os,
                        "link",
                        side_effect=OSError(errno.ENOTSUP, "unsupported"),
                    )
                )
                stack.enter_context(
                    patch.object(
                        app.os, "fsync", side_effect=[None, OSError("disk full")]
                    )
                )
                with self.assertRaises(OSError):
                    app.write_output(dest, "our note")
            self.assertEqual(list(Path(tmp).iterdir()), [])

    @unittest.skipIf(os.name == "nt", "POSIX permission modes")
    def test_new_file_respects_normal_creation_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            normal, dest = Path(tmp) / "normal.md", Path(tmp) / "note.md"
            normal.write_text("normal", encoding="utf-8")
            app.write_output(dest, "new")
            self.assertEqual(
                stat.S_IMODE(dest.stat().st_mode), stat.S_IMODE(normal.stat().st_mode)
            )

    @unittest.skipIf(os.name == "nt", "POSIX permission modes")
    def test_force_preserves_shared_note_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "note.md"
            dest.write_text("old", encoding="utf-8")
            dest.chmod(0o640)
            app.write_output(dest, "new", force=True)
            self.assertEqual(stat.S_IMODE(dest.stat().st_mode), 0o640)

    def test_existing_file_is_never_truncated(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "note.md"
            dest.write_text("my annotations", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                app.write_output(dest, "new")
            self.assertEqual(dest.read_text(), "my annotations")
            self.assertEqual(list(Path(tmp).iterdir()), [dest])

    def test_failed_force_preserves_original_and_cleans_temporary(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "note.md"
            dest.write_text("original", encoding="utf-8")
            with patch.object(app.os, "replace", side_effect=OSError("disk error")):
                with self.assertRaises(OSError):
                    app.write_output(dest, "replacement", force=True)
            self.assertEqual(dest.read_text(), "original")
            self.assertEqual(list(Path(tmp).iterdir()), [dest])

    def test_write_failure_never_publishes_partial_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "note.md"
            with patch.object(app.os, "fsync", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    app.write_output(dest, "new")
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_successful_force_replaces_atomically(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "note.md"
            dest.write_text("old", encoding="utf-8")
            app.write_output(dest, "日本語\nالعربية", force=True)
            self.assertEqual(dest.read_text(encoding="utf-8"), "日本語\nالعربية")
            self.assertEqual(list(Path(tmp).iterdir()), [dest])

    @unittest.skipIf(
        os.name == "nt", "Creating symlinks can require Windows administrator rights"
    )
    def test_force_refuses_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            original, link = Path(tmp) / "original.md", Path(tmp) / "link.md"
            original.write_text("original", encoding="utf-8")
            link.symlink_to(original)
            with self.assertRaisesRegex(OSError, "symbolic link"):
                app.write_output(link, "replacement", force=True)
            self.assertEqual(original.read_text(), "original")

    def test_unicode_filename_fits_byte_limit(self):
        slug = app.slugify("日本語字幕的标题" * 30)
        name = f"2026-09-05_{slug}_[{VIDEO_ID}].md"
        self.assertLess(len(name.encode("utf-8")), 255)
        with tempfile.TemporaryDirectory() as tmp:
            app.write_output(Path(tmp) / name, "caption")

    def test_duplicate_fallback_requires_actual_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "discussion.md"
            note.write_text(
                f'A discussion about video_id: "{VIDEO_ID}"', encoding="utf-8"
            )
            self.assertIsNone(app.find_existing_transcript(VIDEO_ID, Path(tmp)))

    def test_legacy_frontmatter_supports_long_titles_and_yaml_quotes(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "legacy.md"
            for value in [VIDEO_ID, f"'{VIDEO_ID}'", f'"{VIDEO_ID}"']:
                with self.subTest(value=value):
                    note.write_text(
                        f"---\ntitle: {'a' * 600}\nvideo_id: {value}\n---\n",
                        encoding="utf-8",
                    )
                    self.assertEqual(
                        app.find_existing_transcript(VIDEO_ID, Path(tmp)), note
                    )


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="youtube fetcher test ")
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name)
        self.default = track()
        self.dep_patch = patch.object(app, "check_dependencies", return_value=[])
        self.deps = self.dep_patch.start()
        self.addCleanup(self.dep_patch.stop)
        self.api_patch = patch.object(
            YouTubeTranscriptApi, "list", return_value=tracks(self.default)
        )
        self.api = self.api_patch.start()
        self.addCleanup(self.api_patch.stop)
        self.metadata_patch = patch.object(
            app,
            "fetch_video_metadata",
            return_value={
                **app.empty_metadata(),
                "title": "A video",
                "channel": "A channel",
                "metadata_source": "oembed",
            },
        )
        self.metadata = self.metadata_patch.start()
        self.addCleanup(self.metadata_patch.stop)

    def invoke(self, *options, video=VIDEO_ID):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = app.main([*options, "--output-dir", str(self.output), "--", video])
        return result, stdout.getvalue(), stderr.getvalue()

    def test_existing_exact_file_preserved_for_every_format_before_dependencies(self):
        dest = self.output / "valuable.txt"
        dest.write_text("user work", encoding="utf-8")
        self.deps.side_effect = AssertionError("Must not check dependencies")
        for fmt in ["text", "markdown", "json", "srt", "vtt", "txt"]:
            with self.subTest(fmt=fmt):
                code, stdout, stderr = self.invoke("-o", str(dest), "-f", fmt)
                self.assertEqual(code, 3)
                self.assertEqual(stdout, "")
                self.assertIn("preserved", stderr)
                self.assertEqual(dest.read_text(), "user work")
        self.api.assert_not_called()

    def test_default_raw_destinations_are_protected(self):
        for fmt in ["json", "srt", "vtt", "txt"]:
            dest = self.output / f"{VIDEO_ID}.{fmt}"
            dest.write_text("old", encoding="utf-8")
            self.assertEqual(self.invoke("-f", fmt)[0], 3)
            self.assertEqual(dest.read_text(), "old")
        self.api.assert_not_called()

    def test_default_duplicate_is_detected_offline(self):
        dest = self.output / f"2024-01-01_old-title_[{VIDEO_ID}].md"
        dest.write_text("annotated note", encoding="utf-8")
        self.assertEqual(self.invoke()[0], 3)
        self.api.assert_not_called()
        self.deps.assert_not_called()

    def test_force_refreshes_existing_default_note_in_place(self):
        dest = self.output / f"2024-01-01_old-title_[{VIDEO_ID}].md"
        dest.write_text("old", encoding="utf-8")
        self.assertEqual(self.invoke("--force")[0], 0)
        self.assertIn("Hello, world!", dest.read_text())
        self.assertEqual(list(self.output.iterdir()), [dest])

    def test_explicit_output_can_capture_another_language_of_same_video(self):
        old = self.output / f"old_[{VIDEO_ID}].md"
        old.write_text("old English note", encoding="utf-8")
        dest = self.output / "french.md"
        self.api.return_value = tracks(track("fr"))
        self.assertEqual(self.invoke("-o", str(dest), "--lang", "fr")[0], 0)
        self.assertIn('language: "fr"', dest.read_text())
        self.assertEqual(old.read_text(), "old English note")

    def test_stdout_json_is_parseable_and_writes_nothing(self):
        self.api.return_value = tracks(track("fr", text="Voilà 日本語"))
        code, stdout, stderr = self.invoke("--stdout", "-f", "json", "--lang", "auto")
        self.assertEqual(code, 0)
        self.assertEqual(
            json.loads(stdout),
            [{"text": "Voilà 日本語", "start": 65.25, "duration": 2.5}],
        )
        self.assertIn("Selected captions: fr", stderr)
        self.assertEqual(list(self.output.iterdir()), [])
        self.metadata.assert_not_called()

    def test_regional_raw_export_reports_actual_language(self):
        self.api.return_value = tracks(track("es-MX"))
        code, stdout, stderr = self.invoke(
            "--lang", "es", "--format", "json", "--stdout"
        )
        self.assertEqual(code, 0)
        self.assertIsInstance(json.loads(stdout), list)
        self.assertIn("Selected captions: es-MX (manual)", stderr)

    def test_all_exports_have_expected_content(self):
        for fmt, expected in [
            ("srt", "00:01:05,250 --> 00:01:07,750"),
            ("vtt", "WEBVTT"),
            ("txt", "Hello, world!"),
        ]:
            with self.subTest(fmt=fmt):
                self.assertEqual(self.invoke("-f", fmt)[0], 0)
                self.assertIn(expected, (self.output / f"{VIDEO_ID}.{fmt}").read_text())

    def test_markdown_timestamp_links_point_to_caption_start(self):
        code, stdout, _ = self.invoke("--stdout", "--timestamps")
        self.assertEqual(code, 0)
        self.assertIn(
            f"[01:05](https://www.youtube.com/watch?v={VIDEO_ID}&t=65s)", stdout
        )

    def test_no_metadata_does_not_invoke_metadata_providers(self):
        code, stdout, _ = self.invoke("--stdout", "--no-metadata")
        self.assertEqual(code, 0)
        self.metadata.assert_not_called()
        self.assertIn('metadata_source: "skipped"', stdout)
        self.assertIn(VIDEO_ID, stdout)

    def test_translation_keeps_source_and_machine_provenance(self):
        source = track("ja")
        source.translate = Mock(return_value=track("en", True, "Translated text"))
        self.api.return_value = tracks(source)
        code, stdout, stderr = self.invoke(
            "--lang", "auto", "--translate", "en", "--stdout"
        )
        self.assertEqual(code, 0)
        self.assertIn('language: "en"', stdout)
        self.assertIn('source_language: "ja"', stdout)
        self.assertIn('caption_type: "manual"', stdout)
        self.assertIn("translated: true", stdout)
        self.assertIn("machine-translated", stdout)
        self.assertIn("machine translation", stderr)
        source.fetch.assert_not_called()

    def test_same_language_request_does_not_falsely_label_translation(self):
        self.default.translate = Mock(
            side_effect=AssertionError("No translation needed")
        )
        code, stdout, _ = self.invoke("--translate", "en", "--stdout")
        self.assertEqual(code, 0)
        self.assertIn("translated: false", stdout)

    def test_translation_failure_is_actionable_and_saves_nothing(self):
        code, _, stderr = self.invoke("--translate", "fr")
        self.assertEqual(code, 1)
        self.assertIn("cannot translate", stderr)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_list_fetches_no_captions_or_metadata(self):
        code, stdout, _ = self.invoke("--list")
        self.assertEqual(code, 0)
        self.assertIn("[en]", stdout)
        self.default.fetch.assert_not_called()
        self.metadata.assert_not_called()
        self.assertEqual(list(self.output.iterdir()), [])

    def test_blocking_is_not_retried(self):
        self.api.side_effect = RequestBlocked(VIDEO_ID)
        code, stdout, stderr = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn("blocked", stderr)
        self.assertEqual(stdout, "")
        self.assertEqual(self.api.call_count, 1)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_timeout_error_does_not_expose_request_details(self):
        self.api.side_effect = Timeout("secret-proxy-password")
        code, _, stderr = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn("timed out", stderr)
        self.assertNotIn("secret", stderr)

    def test_empty_transcript_is_not_saved_as_success(self):
        self.api.return_value = tracks(track(text=" \n"))
        code, _, stderr = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn("empty captions", stderr)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_invalid_input_is_rejected_before_dependency_work(self):
        self.assertEqual(self.invoke(video="not a video")[0], 1)
        self.deps.assert_not_called()
        self.api.assert_not_called()

    def test_missing_dependency_does_not_contact_youtube(self):
        self.deps.return_value = [
            {
                "name": "youtube-transcript-api",
                "type": "python",
                "install": "install command",
            }
        ]
        self.assertEqual(self.invoke()[0], 2)
        self.api.assert_not_called()

    def test_invalid_timeout_is_a_usage_error(self):
        for value in ["0", "-1", "nan", "inf"]:
            with self.subTest(value=value), self.assertRaises(SystemExit) as caught:
                self.invoke("--timeout", value)
            self.assertEqual(caught.exception.code, 2)

    def test_output_io_error_has_no_traceback(self):
        self.output.joinpath("parent-file").write_text("original", encoding="utf-8")
        code, _, stderr = self.invoke(
            "-o", str(self.output / "parent-file" / "note.md")
        )
        self.assertEqual(code, 1)
        self.assertIn("Check the path", stderr)
        self.assertNotIn("Traceback", stderr)


class NetworkTests(unittest.TestCase):
    def test_timeout_applies_to_caption_get_and_post(self):
        with contextlib.ExitStack() as stack:
            session = stack.enter_context(app.create_http_session(7))
            request = stack.enter_context(patch.object(Session, "request"))
            session.get("https://example.invalid")
            session.post("https://example.invalid", json={})
            self.assertEqual(
                [c.kwargs["timeout"] for c in request.call_args_list], [7, 7]
            )

    def test_metadata_subprocess_ignores_user_config_and_is_bounded(self):
        result = Mock(
            returncode=0, stdout=json.dumps({"title": "日本語", "duration": 10})
        )
        with contextlib.ExitStack() as stack:
            stack.enter_context(
                patch.object(app.shutil, "which", return_value="yt-dlp")
            )
            run = stack.enter_context(
                patch.object(app.subprocess, "run", return_value=result)
            )
            metadata = app.fetch_video_metadata(VIDEO_ID, timeout=4)
        self.assertEqual(metadata["title"], "日本語")
        command = run.call_args.args[0]
        self.assertIn("--ignore-config", command)
        self.assertIn("--no-playlist", command)
        self.assertIn("--no-cache-dir", command)
        self.assertEqual(run.call_args.kwargs["timeout"], 8)

    def test_metadata_failure_does_not_discard_captions(self):
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(app.shutil, "which", return_value=None))
            stack.enter_context(patch("requests.get", side_effect=Timeout))
            stderr = stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
            metadata = app.fetch_video_metadata(VIDEO_ID)
        self.assertEqual(metadata["metadata_source"], "unavailable")
        self.assertIn("metadata is unavailable", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
