import copy
import json
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path

from cloudseed.exporter import bibliography, export_files, save_result, zip_bytes
from cloudseed.pipeline import parse_json, run_pipeline, validate_stage
from cloudseed.sources import load_sources, validate_sources, DEFAULT_TOPIC


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.sources = load_sources()
        self.result = run_pipeline(self.sources, mode="demo")

    def test_demo_completes_four_stages_and_exports(self):
        self.assertEqual(len(self.result["trace"]), 4)
        self.assertEqual(self.result["meta"]["mode"], "demo")
        self.assertTrue(all(t["attempts"] == 0 for t in self.result["trace"]))
        files = export_files(self.result)
        self.assertIn("离线手写示例", files["report.md"])
        self.assertIn("P1-E1", files["report.md"])
        self.assertIn("obsidian/03_Topics/Topic Pool/T1.md", files)

    def test_offline_fixture_cannot_pretend_to_analyse_custom_topic(self):
        with self.assertRaisesRegex(ValueError, "离线示例"):
            run_pipeline(self.sources, topic="另一个研究问题", mode="demo")

    def test_offline_fixture_rejects_changed_source_text(self):
        changed = copy.deepcopy(self.sources)
        changed[0]["pages"][0]["text"] = "新的论文内容"
        with self.assertRaisesRegex(ValueError, "离线示例"):
            run_pipeline(changed, mode="demo")

    def test_unknown_evidence_identifier_rejected(self):
        ideas = copy.deepcopy(self.result["ideas"])
        ideas["ideas"][0]["evidence_ids"] = ["P99-E1"]
        with self.assertRaisesRegex(ValueError, "不存在"):
            validate_stage("ideas", ideas, self.sources)

    def test_single_paper_claim_cannot_cite_another_source(self):
        analysis = copy.deepcopy(self.result["analysis"])
        analysis["papers"][0]["findings"][0]["evidence_ids"] = ["P2-E1"]
        with self.assertRaisesRegex(ValueError, "其他资料"):
            validate_stage("analysis", analysis, self.sources)

    def test_missing_and_duplicate_papers_rejected(self):
        analysis = copy.deepcopy(self.result["analysis"])
        analysis["papers"].pop()
        with self.assertRaises(ValueError):
            validate_stage("analysis", analysis, self.sources)

    def test_metadata_only_and_unsafe_ids_rejected(self):
        changed = copy.deepcopy(self.sources)
        changed[0]["pages"] = []
        with self.assertRaisesRegex(ValueError, "没有可分析"):
            validate_sources(changed)
        changed = copy.deepcopy(self.sources)
        changed[0]["id"] = "../../escape"
        with self.assertRaises(ValueError):
            validate_sources(changed)

    def test_json_truncation_and_prose_rejected(self):
        self.assertEqual(parse_json('```json\n{"ok":true}\n```'), {"ok": True})
        for text in ['{"ok":', '解释 {"ok":true}', '{"ok":true}{"other":true}']:
            with self.assertRaises(ValueError):
                parse_json(text)

    def test_zip_and_export_do_not_contain_configuration(self):
        with zipfile.ZipFile(BytesIO(zip_bytes(self.result))) as archive:
            self.assertEqual(len(archive.namelist()), 11)
            self.assertFalse(any(".env" in name for name in archive.namelist()))
            parsed = json.loads(archive.read("result.json"))
            self.assertEqual(parsed["meta"]["topic"], DEFAULT_TOPIC)

    def test_bibtex_uses_supplied_metadata_and_escapes_symbols(self):
        changed = copy.deepcopy(self.sources)
        changed[0]["title"] = "Test & A_B {study}"
        bib = bibliography(changed)
        self.assertIn(r"Test \& A\_B \{study\}", bib)
        self.assertIn("10.48550/arXiv.2607.05050", bib)

    def test_additive_vault_export_preserves_existing_note(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            vault = root / "vault"
            vault.mkdir()
            existing = vault / "P1.md"
            existing.write_text("人工笔记", encoding="utf-8")
            out, batch = save_result(self.result, root / "run", vault)
            self.assertEqual(existing.read_text(encoding="utf-8"), "人工笔记")
            self.assertTrue((batch / "01_Sources/Papers/P1.md").is_file())
            with self.assertRaises(FileExistsError):
                save_result(self.result, out)


if __name__ == "__main__":
    unittest.main()
