import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("MODEL_ID", "test-model")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from coding_assistant.tools import tools
from coding_assistant.tools.registry import assemble_tool_pool


class SearchTextTests(unittest.TestCase):
    def test_rg_is_preferred_when_available(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch.object(tools.shutil, "which", return_value="rg"),
                patch.object(
                    tools, "_search_with_rg",
                    return_value=(["sample.py:1:1:needle"], False),
                ) as rg_search,
            ):
                result = tools.run_search_text("needle", cwd=root)
            rg_search.assert_called_once()
            self.assertIn("Search backend: rg", result)

    def test_python_fallback_honors_glob_case_and_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "one.py").write_text("Needle\nneedle\n", encoding="utf-8")
            (root / "two.txt").write_text("NEEDLE\n", encoding="utf-8")
            with patch.object(tools.shutil, "which", return_value=None):
                result = tools.run_search_text(
                    "needle", glob="*.py", case_sensitive=False,
                    max_results=1, cwd=root
                )
            self.assertIn("Search backend: python", result)
            self.assertIn("limit reached: 1", result)
            self.assertIn("one.py:1:1:Needle", result)
            self.assertNotIn("two.txt", result)

    def test_python_fallback_skips_build_artifacts(self):
        # Reproduces the 24MB freeze: a broad query must not walk into
        # node_modules/ or dist/ and return megabytes of minified matches.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("needle\n", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "lib.min.js").write_text(
                "x" * 5_000_000 + "needle", encoding="utf-8")
            (root / "dist").mkdir()
            (root / "dist" / "bundle.js").write_text(
                "y" * 5_000_000 + "needle", encoding="utf-8")
            with patch.object(tools.shutil, "which", return_value=None):
                result = tools.run_search_text("needle", cwd=root)
        self.assertIn("src/app.py", result)
        self.assertNotIn("node_modules", result)
        self.assertNotIn("dist", result)
        self.assertLess(len(result), 50_000)

    def test_python_fallback_truncates_long_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            long_line = "A" * 1000 + "needle" + "B" * 1000
            (root / "big.py").write_text(long_line + "\n", encoding="utf-8")
            with patch.object(tools.shutil, "which", return_value=None):
                result = tools.run_search_text("needle", cwd=root)
        self.assertIn("\u2026", result)
        for line in result.splitlines():
            if "big.py" in line:
                # content after the third ':' is the (truncated) source line
                content = line.split(":", 3)[3]
                self.assertLessEqual(len(content), tools.SEARCH_MAX_COLUMNS + 1)

    def test_python_fallback_honors_gitignore(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".gitignore").write_text("secret.txt\n", encoding="utf-8")
            (root / "secret.txt").write_text("needle\n", encoding="utf-8")
            (root / "visible.txt").write_text("needle\n", encoding="utf-8")
            with patch.object(tools.shutil, "which", return_value=None):
                result = tools.run_search_text("needle", cwd=root)
        self.assertIn("visible.txt", result)
        self.assertNotIn("secret.txt", result)

    def test_python_fallback_expands_brace_globs(self):
        # Regression: 'src/**/*.{vue,ts}' silently matched nothing because
        # fnmatch has no brace support, and the agent concluded the symbol
        # did not exist.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src" / "pages").mkdir(parents=True)
            (root / "src" / "pages" / "Widget.vue").write_text(
                "needle\n", encoding="utf-8")
            (root / "src" / "types.ts").write_text("needle\n", encoding="utf-8")
            (root / "src" / "README.md").write_text("needle\n", encoding="utf-8")
            with patch.object(tools.shutil, "which", return_value=None):
                result = tools.run_search_text(
                    "needle", glob="src/**/*.{vue,ts}", cwd=root)
        self.assertIn("Widget.vue", result)
        self.assertIn("types.ts", result)
        self.assertNotIn("README.md", result)

    def test_path_parameter_scopes_search(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "inner.py").write_text("needle\n", encoding="utf-8")
            (root / "outer.py").write_text("needle\n", encoding="utf-8")
            with patch.object(tools.shutil, "which", return_value=None):
                result = tools.run_search_text("needle", path="src", cwd=root)
        self.assertIn("inner.py", result)
        self.assertNotIn("outer.py", result)

    def test_path_parameter_accepts_single_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.py").write_text("needle\n", encoding="utf-8")
            (root / "b.py").write_text("needle\n", encoding="utf-8")
            with patch.object(tools.shutil, "which", return_value=None):
                result = tools.run_search_text("needle", path="a.py", cwd=root)
        self.assertIn("a.py:1", result)
        self.assertNotIn("b.py", result)

    def test_search_inside_excluded_directory_is_reported_not_silent(self):
        # Regression: searching node_modules returned a misleading
        # "(no matches)" and the agent kept probing library internals.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "node_modules" / "lib").mkdir(parents=True)
            (root / "node_modules" / "lib" / "x.js").write_text(
                "needle\n", encoding="utf-8")
            with patch.object(tools.shutil, "which", return_value=None):
                result = tools.run_search_text(
                    "needle", path="node_modules/lib", cwd=root)
        self.assertIn("excluded directory", result)
        self.assertIn("node_modules", result)

    def test_search_path_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertIn("escapes workspace",
                          tools.run_search_text("x", path="../elsewhere", cwd=root))
            self.assertIn("not found",
                          tools.run_search_text("x", path="missing_dir", cwd=root))
            self.assertIn("non-empty string",
                          tools.run_search_text("x", path="", cwd=root))

    def test_search_output_is_size_capped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for i in range(50):
                (root / f"f{i}.txt").write_text(
                    "needle line content here\n", encoding="utf-8")
            with patch.object(tools.shutil, "which", return_value=None):
                with patch.object(tools, "SEARCH_MAX_OUTPUT_CHARS", 500):
                    result = tools.run_search_text("needle", cwd=root)
        self.assertIn("truncated", result)
        self.assertLessEqual(len(result), 500 + 400)


class ApplyPatchTests(unittest.TestCase):
    def test_multiple_files_and_multiple_hunks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.py"
            second = root / "second.py"
            first.write_text("alpha\nbeta\n", encoding="utf-8")
            second.write_text("one\ntwo\n", encoding="utf-8")
            result = tools.run_apply_patch([
                {"path": "first.py", "hunks": [
                    {"old_text": "alpha", "new_text": "ALPHA"},
                    {"old_text": "beta", "new_text": "BETA"},
                ]},
                {"path": "second.py", "hunks": [
                    {"old_text": "one", "new_text": "ONE"},
                ]},
            ], cwd=root)
            self.assertIn("Patched 2 file(s), 3 hunk(s)", result)
            self.assertEqual(first.read_text(encoding="utf-8"), "ALPHA\nBETA\n")
            self.assertEqual(second.read_text(encoding="utf-8"), "ONE\ntwo\n")

    def test_context_failure_is_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.py"
            second = root / "second.py"
            first.write_text("before\n", encoding="utf-8")
            second.write_text("unchanged\n", encoding="utf-8")
            result = tools.run_apply_patch([
                {"path": "first.py", "hunks": [
                    {"old_text": "before", "new_text": "after"},
                ]},
                {"path": "second.py", "hunks": [
                    {"old_text": "missing", "new_text": "new"},
                ]},
            ], cwd=root)
            self.assertIn("context mismatch", result)
            self.assertEqual(first.read_text(encoding="utf-8"), "before\n")
            self.assertEqual(second.read_text(encoding="utf-8"), "unchanged\n")

    def test_sha_and_workspace_boundary_are_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.py"
            target.write_text("old\n", encoding="utf-8")
            wrong_sha = hashlib.sha256(b"different").hexdigest()
            result = tools.run_apply_patch([
                {"path": "target.py", "expected_sha256": wrong_sha,
                 "hunks": [{"old_text": "old", "new_text": "new"}]},
            ], cwd=root)
            self.assertIn("stale file", result)
            self.assertIn("old", target.read_text(encoding="utf-8"))
            result = tools.run_apply_patch([
                {"path": "../outside.py", "hunks": [
                    {"old_text": "old", "new_text": "new"},
                ]},
            ], cwd=root)
            self.assertIn("Path escapes workspace", result)


class RegistryTests(unittest.TestCase):
    def test_new_tools_are_registered(self):
        schemas, handlers = assemble_tool_pool()
        names = {schema["name"] for schema in schemas}
        self.assertIn("search_text", names)
        self.assertIn("apply_patch", names)
        self.assertIn("search_text", handlers)
        self.assertIn("apply_patch", handlers)

    def test_list_dir_is_registered(self):
        schemas, handlers = assemble_tool_pool(include_all=True)
        names = {schema["name"] for schema in schemas}
        self.assertIn("list_dir", names)
        self.assertIn("list_dir", handlers)

    def test_bash_description_is_platform_aware(self):
        from coding_assistant.core.platform import platform_facts
        bash_tool = next(t for t in assemble_tool_pool(include_all=True)[0]
                         if t["name"] == "bash")
        facts = platform_facts()
        self.assertIn(facts["native_shell"], bash_tool["description"])


class PlatformCompatTests(unittest.TestCase):
    def test_glob_is_recursive(self):
        # Without recursive=True, "**/*.py" only matches the top level and the
        # model would conclude files don't exist -> falls back to bash find.
        shallow = tools.run_glob("*.py")
        deep = tools.run_glob("**/*.py")
        self.assertGreater(len(deep.splitlines()), len(shallow.splitlines()))

    def test_run_list_dir_lists_entries_with_markers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a_file.py").write_text("x", encoding="utf-8")
            (root / "a_dir").mkdir()
            out = tools.run_list_dir(".", cwd=root)
            self.assertIn("a_file.py", out)
            self.assertIn("a_dir/", out)

    def test_call_tool_handler_drops_invented_kwargs(self):
        def handler(path: str, limit: int = 0) -> str:
            return path

        result = tools.call_tool_handler(
            handler, {"path": "ok", "bogus": 123, "limit": 5}, "handler")
        self.assertEqual(result, "ok")

    def test_decode_output_preserves_cjk_under_any_codec(self):
        for encoded in ("utf-8", "gb18030", "cp936"):
            raw = "错误处理: 文件不存在".encode(encoded)
            self.assertEqual(tools._decode_output(raw), "错误处理: 文件不存在")

    def test_platform_brief_is_nonempty(self):
        from coding_assistant.core.platform import platform_brief
        self.assertTrue(platform_brief())


class ReadCacheTests(unittest.TestCase):
    """read_file must not re-read unchanged files forever (the compact loop)."""

    def setUp(self):
        tools._FILE_CACHE.clear()
        tools._READ_REPEAT.clear()

    def tearDown(self):
        tools._FILE_CACHE.clear()
        tools._READ_REPEAT.clear()

    def test_repeat_read_of_unchanged_file_returns_cache_hit_note(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "keep.py").write_text("alpha\nbeta\n", encoding="utf-8")
            first = tools.run_read("keep.py", cwd=root)
            second = tools.run_read("keep.py", cwd=root)
            third = tools.run_read("keep.py", cwd=root)
        self.assertNotIn("cache hit", first)
        self.assertIn("cache hit", second)
        # The earlier copy is already in context; re-sending it would double
        # the context cost and defeat message-level dedup.
        self.assertNotIn("alpha", second)
        self.assertIn("cache hit", third)
        self.assertEqual(list(tools._READ_REPEAT.values())[0], 3)

    def test_followup_read_of_a_different_range_is_served(self):
        # Regression: the repeat guard counted per path, so reading the
        # second half of a file (offset) after a truncated first read
        # (limit) was refused with "already been read".
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lines = [f"line{i}" for i in range(1, 201)]
            (root / "big.vue").write_text("\n".join(lines), encoding="utf-8")
            head = tools.run_read("big.vue", limit=140, cwd=root)
            tail = tools.run_read("big.vue", offset=140, cwd=root)
        self.assertIn("line1", head)
        self.assertIn("more lines", head)
        self.assertIn("line141", tail)
        self.assertIn("line200", tail)
        self.assertNotIn("Error", tail)

    def test_reset_read_repeat_counters_allows_post_compaction_reread(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "keep.py").write_text("alpha\n", encoding="utf-8")
            for _ in range(tools.MAX_READ_REPEATS + 1):
                tools.run_read("keep.py", cwd=root)
            tools.reset_read_repeat_counters()
            fresh = tools.run_read("keep.py", cwd=root)
        self.assertIn("alpha", fresh)

    def test_repeat_read_beyond_guard_stops_re_serving_full_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "keep.py").write_text("alpha\nbeta\n", encoding="utf-8")
            for _ in range(tools.MAX_READ_REPEATS + 1):
                tools.run_read("keep.py", cwd=root)
            guarded = tools.run_read("keep.py", cwd=root)
        self.assertIn("already been read", guarded)
        self.assertNotIn("alpha", guarded)  # full content withheld to break loop

    def test_edit_invalidates_cache_so_next_read_is_fresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "keep.py").write_text("alpha\n", encoding="utf-8")
            tools.run_read("keep.py", cwd=root)
            tools.run_edit("keep.py", "alpha", "alpha-changed", cwd=root)
            fresh = tools.run_read("keep.py", cwd=root)
        self.assertIn("alpha-changed", fresh)
        self.assertEqual(list(tools._READ_REPEAT.values())[0], 1)

    def test_changed_file_mtime_bypasses_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "keep.py"
            target.write_text("v1\n", encoding="utf-8")
            tools.run_read("keep.py", cwd=root)
            target.write_text("v2\n", encoding="utf-8")
            # Two rapid writes can share one mtime_ns tick on NTFS; force a
            # visible change so the cache bypass is deterministic.
            stat = target.stat()
            os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
            fresh = tools.run_read("keep.py", cwd=root)
        self.assertIn("v2", fresh)
        self.assertEqual(list(tools._READ_REPEAT.values())[0], 1)


class RangeCoverageTests(unittest.TestCase):
    """Re-reads fully covered by earlier served ranges must not re-serve
    content, even when the model varies offset/limit to dodge the per-range
    repeat guard (observed: a model paged through one bundle 3 times)."""

    def setUp(self):
        tools.reset_read_repeat_counters()
        tools._FILE_CACHE.clear()

    def tearDown(self):
        tools.reset_read_repeat_counters()
        tools._FILE_CACHE.clear()

    def test_covered_reread_with_different_range_returns_note(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lines = [f"line{i}" for i in range(1, 201)]
            (root / "big.vue").write_text("\n".join(lines), encoding="utf-8")
            tools.run_read("big.vue", limit=200, cwd=root)
            covered = tools.run_read("big.vue", offset=50, limit=100, cwd=root)
        self.assertIn("fully covered", covered)
        self.assertNotIn("line51", covered)

    def test_partially_uncovered_followup_is_still_served(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lines = [f"line{i}" for i in range(1, 201)]
            (root / "big.vue").write_text("\n".join(lines), encoding="utf-8")
            tools.run_read("big.vue", limit=150, cwd=root)
            tail = tools.run_read("big.vue", offset=150, limit=100, cwd=root)
        self.assertIn("line151", tail)
        self.assertNotIn("fully covered", tail)

    def test_edit_invalidates_served_ranges(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "keep.py").write_text("alpha\nbeta\n", encoding="utf-8")
            tools.run_read("keep.py", cwd=root)
            tools.run_edit("keep.py", "alpha", "gamma", cwd=root)
            fresh = tools.run_read("keep.py", cwd=root)
        self.assertIn("gamma", fresh)
        self.assertNotIn("fully covered", fresh)


class DependencyReadCapTests(unittest.TestCase):
    """Reads under node_modules/dist/build are limited to one small
    declaration file: library internals are answered from the project's own
    usage, not from minified source (observed: 15 calls reading
    ant-design-vue internals in one session, zero edits)."""

    def setUp(self):
        tools.reset_read_repeat_counters()
        tools._FILE_CACHE.clear()

    def tearDown(self):
        tools.reset_read_repeat_counters()
        tools._FILE_CACHE.clear()

    def test_implementation_files_in_dependency_tree_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pkg = root / "node_modules" / "lib"
            pkg.mkdir(parents=True)
            (pkg / "Select.js").write_text("minified junk\n", encoding="utf-8")
            result = tools.run_read("node_modules/lib/Select.js", cwd=root)
        self.assertIn("refused", result)
        self.assertNotIn("minified", result)
        # The refusal must redirect to project-local usage instead of
        # inviting a read_file retry through another path.
        self.assertIn("search_text", result)

    def test_declaration_file_is_served_once_then_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pkg = root / "node_modules" / "lib"
            pkg.mkdir(parents=True)
            (pkg / "index.d.ts").write_text(
                "export declare const props: {\n  value: any;\n};\n",
                encoding="utf-8")
            (pkg / "other.d.ts").write_text("export declare const b: 1;\n",
                                            encoding="utf-8")
            first = tools.run_read("node_modules/lib/index.d.ts", cwd=root)
            second = tools.run_read("node_modules/lib/other.d.ts", cwd=root)
        self.assertIn("props", first)
        self.assertIn("refused", second)
        self.assertNotIn("export declare const b", second)

    def test_missing_dependency_file_does_not_consume_budget(self):
        """A guessed path that does not exist must not spend the single
        allowed .d.ts read — one session lost the budget to a mistyped path
        and then had the real declaration file refused."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pkg = root / "node_modules" / "lib"
            pkg.mkdir(parents=True)
            (pkg / "index.d.ts").write_text(
                "export declare const props: any;\n", encoding="utf-8")
            missed = tools.run_read("node_modules/lib/Absent.d.ts", cwd=root)
            served = tools.run_read("node_modules/lib/index.d.ts", cwd=root)
        self.assertIn("Error", missed)
        self.assertIn("props", served)

    def test_dependency_declaration_read_is_line_capped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pkg = root / "node_modules" / "lib"
            pkg.mkdir(parents=True)
            lines = "\n".join(f"declare const l{i}: number;" for i in range(500))
            (pkg / "index.d.ts").write_text(lines, encoding="utf-8")
            served = tools.run_read(
                "node_modules/lib/index.d.ts", limit=500, cwd=root)
        self.assertIn("l0", served)
        self.assertNotIn("l499", served)
        self.assertIn("more lines", served)

    def test_compaction_reset_restores_dependency_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pkg = root / "node_modules" / "lib"
            pkg.mkdir(parents=True)
            (pkg / "a.d.ts").write_text("export declare const a: 1;\n",
                                        encoding="utf-8")
            tools.run_read("node_modules/lib/a.d.ts", cwd=root)
            tools.run_read("node_modules/lib/a.d.ts", cwd=root)
            tools.reset_read_repeat_counters()
            fresh = tools.run_read("node_modules/lib/a.d.ts", cwd=root)
        self.assertIn("declare", fresh)


class SearchPathSuggestionTests(unittest.TestCase):
    def test_missing_path_suggests_same_basename_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pages = root / "src" / "pages"
            pages.mkdir(parents=True)
            (pages / "FeedbackPage.vue").write_text("<template/>\n",
                                                    encoding="utf-8")
            with patch.object(tools.shutil, "which", return_value=None):
                result = tools.run_search_text(
                    "needle", path="src/pages/feedback/FeedbackPage.vue",
                    cwd=root)
        self.assertIn("search path not found", result)
        self.assertIn("Did you mean", result)
        self.assertIn("src/pages/FeedbackPage.vue", result)

    def test_missing_path_without_candidates_has_no_suggestion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "unrelated.py").write_text("needle\n", encoding="utf-8")
            with patch.object(tools.shutil, "which", return_value=None):
                result = tools.run_search_text(
                    "needle", path="src/nope/Missing.vue", cwd=root)
        self.assertIn("search path not found", result)
        self.assertNotIn("Did you mean", result)


class GlobExclusionTests(unittest.TestCase):
    """glob must not surface dependency/build matches: one session's
    `**/foo*` returned dist bundle paths and an explicit node_modules glob
    handed the model a readable file list that defeated the read guards."""

    def test_build_output_matches_are_filtered_with_note(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "selectModel.vue").write_text("x\n",
                                                          encoding="utf-8")
            (root / "dist" / "assets").mkdir(parents=True)
            (root / "dist" / "assets" / "selectModel-abc.js").write_text(
                "x\n", encoding="utf-8")
            result = tools.run_glob("**/selectModel*", cwd=root)
        self.assertIn("src", result)
        self.assertNotIn("dist", result.split("hidden")[0])
        self.assertIn("hidden", result)

    def test_excluded_only_glob_returns_guard_message(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pkg = root / "node_modules" / "ant-design-vue" / "es" / "select"
            pkg.mkdir(parents=True)
            (pkg / "index.d.ts").write_text("export {}\n", encoding="utf-8")
            result = tools.run_glob(
                "node_modules/ant-design-vue/es/select/**/*.d.ts", cwd=root)
        self.assertIn("excluded", result)
        self.assertIn("search the project source", result)
        self.assertNotIn("index.d.ts\n", result)

    def test_clean_glob_has_no_exclusion_note(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "app.vue").write_text("x\n", encoding="utf-8")
            result = tools.run_glob("src/*.vue", cwd=root)
        self.assertIn("app.vue", result)
        self.assertNotIn("hidden", result)


if __name__ == "__main__":
    unittest.main()
