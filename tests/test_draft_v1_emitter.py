"""Synthetic producer and publication checks; no benchmark PDF is opened."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/paes-importer/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from draft_contract import DraftContractError, validate_v1
from draft_v1_emitter import (
    assemble_v1, publish_verified, source_key, source_paths_from_manifest, source_records,
    staging_directory,
)
from import_benchmark import _SOURCE_IDS, generate_draft
from test_draft_contract_v1 import digest, fixture


class PdfTextObj:
    def __init__(self, bbox):
        self.bbox = bbox

    def get_bounds(self):
        return self.bbox

    def get_font_size(self):
        return 1

    def get_matrix(self):
        return SimpleNamespace(a=12, b=0, c=0, d=12)


class _SyntheticLayoutObject:
    def __init__(self, bbox):
        self.bbox = bbox

    def get_bounds(self):
        return self.bbox


class _SyntheticBitmap:
    def to_pil(self):
        return Image.new("RGB", (1200, 1600), "white")


class _SyntheticPage:
    def __init__(self):
        self.objects = [
            PdfTextObj((65, 700, 79, 714)),
            PdfTextObj((90, 700, 190, 712)),
        ]

    def get_size(self):
        return 600, 800

    def get_objects(self):
        return list(self.objects)

    def render(self, *, scale=2, crop=None):
        return _SyntheticBitmap()


class _SyntheticPdf:
    def __init__(self):
        self.page = _SyntheticPage()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def __len__(self):
        return 1

    def __getitem__(self, index):
        if index != 0:
            raise IndexError(index)
        return self.page


class _SyntheticThreePagePdf:
    def __init__(self):
        self.pages = [_SyntheticPage() for _ in range(3)]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def __len__(self):
        return len(self.pages)

    def __getitem__(self, index):
        return self.pages[index]


class DraftV1EmitterTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.draft = fixture(self.root)

    def assemble(self, draft=None):
        return assemble_v1(
            self.draft if draft is None else draft,
            sources=self.draft["sources"], selection_sha256=digest(b"fixed cases"),
            artifact_root=self.root, sha256_file=lambda p: digest(p.read_bytes()),
        )

    def test_emission_preserves_math_assets_and_evidence(self):
        original = copy.deepcopy(self.draft)
        self.draft["source_objects"][0]["representation"] = ["math", "text"]
        self.draft["source_objects"][0]["parent_id"] = "raw-page-atom"
        result = self.assemble()
        validate_v1(result, artifact_root=self.root, check_files=True)
        self.assertEqual(result["questions"][0]["stem"], original["questions"][0]["stem"])
        self.assertEqual(result["assets"], original["assets"])
        self.assertEqual(result["evidence"][0]["sha256"], digest(b"evidence bytes"))
        self.assertEqual(result["source_objects"][0]["extensions"], {
            "paessed.representation_types": ["math", "text"],
            "paessed.raw_parent_source_id": "raw-page-atom",
        })
        self.assertEqual(self.draft["source_objects"][0]["parent_id"], "raw-page-atom")

    def test_distinct_same_year_sources_and_unmapped_source(self):
        self.assertNotEqual(source_key({"year": 2026, "source": "pdf-a"}),
                            source_key({"year": 2026, "source": "pdf-b"}))
        self.draft["pages"][0]["source_id"] = "unknown"
        with self.assertRaisesRegex(DraftContractError, "Page lacks mapped source"):
            self.assemble()

    def test_duplicate_question_id_aborts(self):
        self.draft["questions"].append(copy.deepcopy(self.draft["questions"][0]))
        with self.assertRaisesRegex(DraftContractError, "Duplicate question IDs"):
            self.assemble()

    def test_invalid_cross_reference_aborts_without_demotion(self):
        self.draft["questions"][0]["region_ids"] = ["missing-region"]
        with self.assertRaisesRegex(DraftContractError, "Unknown region"):
            self.assemble()

    def test_unproven_math_demotes_complete_with_evidence(self):
        question = self.draft["questions"][0]
        question["stem"][0]["structural_fidelity"]["status"] = "unresolved"
        result = self.assemble()
        self.assertEqual(result["questions"][0]["extraction_status"], "partial")
        self.assertEqual(result["questions"][0]["stem"][0]["type"], "math")
        issue = result["issues"][-1]
        self.assertEqual(issue["code"], "V1_STRUCTURAL_INCOMPLETE")
        self.assertTrue(issue["blocks_completion"])
        self.assertIn("ev-a", issue["evidence_ids"])
        validate_v1(result, artifact_root=self.root, check_files=True)

    def test_ambiguous_unresolved_stem_demotes_complete(self):
        self.draft["questions"][0]["stem"][0] = {
            "type": "unresolved", "reason": "ambiguous_math_operand",
            "evidence_id": "ev-a", "source_ids": ["atom-math"], "owner": "ambiguous",
        }
        result = self.assemble()
        self.assertEqual(result["questions"][0]["extraction_status"], "partial")
        self.assertEqual(result["questions"][0]["stem"][0]["owner"], "ambiguous")
        self.assertEqual(result["issues"][-1]["code"], "V1_STRUCTURAL_INCOMPLETE")

    def test_text_rendering_is_not_a_second_semantic_operand(self):
        rendering = {"id": "glyph-render", "region_id": "region-a", "owner": "stem",
                     "kind": "text_rendering", "candidate_type": "layout",
                     "bbox": [10, 500, 100, 550],
                     "extensions": {"paessed.effective_font_size": 12,
                                    "paessed.pdfium_declared_font_size": 1,
                                    "paessed.pdfium_vertical_scale": 12}}
        self.draft["source_objects"][0].setdefault("extensions", {})[
            "paessed.source_font_size"] = 12
        self.draft["source_objects"].append(rendering)
        result = self.assemble()
        self.assertEqual(result["questions"][0]["extraction_status"], "complete")
        self.assertEqual(result["source_objects"][-1]["extensions"]["paessed.duplicate_of"],
                         ["atom-math"])

        rendering["bbox"] = [150, 500, 170, 520]
        result = self.assemble()
        self.assertEqual(result["questions"][0]["extraction_status"], "partial")
        self.assertEqual(result["issues"][-1]["code"], "V1_STRUCTURAL_INCOMPLETE")
        self.assertTrue(result["issues"][-1]["evidence_ids"])
        self.assertIn(rendering["id"], {obj["id"] for obj in result["source_objects"]})

    def test_forged_text_rendering_duplicate_reference_is_rejected(self):
        rendering = {"id": "glyph-render", "region_id": "region-a", "owner": "stem",
                     "kind": "text_rendering", "candidate_type": "layout",
                     "bbox": [150, 500, 170, 520],
                     "extensions": {"paessed.duplicate_of": ["atom-math"]}}
        self.draft["source_objects"].append(rendering)

        with self.assertRaisesRegex(DraftContractError, "Invalid text rendering provenance"):
            self.assemble()

    def test_inconsistent_effective_text_rendering_size_is_rejected(self):
        self.draft["source_objects"][0].setdefault("extensions", {})[
            "paessed.source_font_size"] = 12
        self.draft["source_objects"].append({
            "id": "glyph-render", "region_id": "region-a", "owner": "stem",
            "kind": "text_rendering", "candidate_type": "layout",
            "bbox": [10, 500, 100, 550],
            "extensions": {
                "paessed.effective_font_size": 12,
                "paessed.pdfium_declared_font_size": 1,
                "paessed.pdfium_vertical_scale": 8,
            },
        })

        with self.assertRaisesRegex(DraftContractError, "Invalid text rendering font metrics"):
            self.assemble()

    def _synthetic_generator_inputs(self):
        source = self.root / "synthetic.pdf"
        source.write_bytes(b"synthetic controlled fixture")
        cases_path = self.root / "cases.json"
        cases_path.write_text(json.dumps({"cases": [{
            "id": "fixture-q1", "year": 2030, "question": "1", "page": 1,
        }]}), encoding="utf-8")
        items = [
            SimpleNamespace(page=1, text="1.", x=65, y=700, width=14, height=14, font_size=12),
            SimpleNamespace(page=1, text="El valor es cuatro.", x=90, y=700, width=100, height=12, font_size=12),
        ]
        for index, label in enumerate("ABCD"):
            y = 660 - index * 22
            items.append(SimpleNamespace(page=1, text=f"{label})", x=90, y=y,
                                         width=15, height=12, font_size=12))
            items.append(SimpleNamespace(page=1, text=f"Alternativa {label}", x=120, y=y,
                                         width=70, height=12, font_size=12))
        return cases_path, source, items

    def _generate_fixture(self, stage):
        cases_path, source, items = self._synthetic_generator_inputs()
        with patch("pypdfium2.PdfDocument", return_value=_SyntheticPdf()), \
                patch("import_benchmark.extract_text_with_positions", return_value=items):
            result = generate_draft(cases_path, stage, {"2030": source})
        return result

    def _generate_footer_fixture(self, stage, *, nearby_option_marker=False,
                                 bottom_layout_object=False,
                                 near_footer_layout_object=False,
                                 straddling_footer_text_object=False,
                                 nearby_pdf_text_object=False):
        source = self.root / "synthetic-footer.pdf"
        source.write_bytes(b"synthetic repeated footer fixture")
        cases_path = self.root / "footer-cases.json"
        cases_path.write_text(json.dumps({"cases": [
            {"id": f"footer-fixture-page-{page}", "year": 2030,
             "question": "1", "page": page}
            for page in (1, 2, 3)
        ]}), encoding="utf-8")
        items = []
        for page in (1, 2, 3):
            items.extend([
                SimpleNamespace(page=page, text="1.", x=65, y=700, width=14, height=14, font_size=12),
                SimpleNamespace(page=page, text="El valor es cuatro.", x=90, y=700, width=100, height=12, font_size=12),
            ])
            if nearby_pdf_text_object:
                items.append(SimpleNamespace(page=page, text="Texto cercano", x=295, y=45,
                                             width=65, height=12, font_size=12))
            option_ys = [660, 638, 616, 50 if nearby_option_marker else 594]
            for label, y in zip("ABCD", option_ys):
                items.append(SimpleNamespace(page=page, text=f"{label})", x=90, y=y,
                                             width=15, height=12, font_size=12))
                items.append(SimpleNamespace(page=page, text=f"Alternativa {label}", x=120, y=y,
                                             width=70, height=12, font_size=12))
            items.append(SimpleNamespace(page=page, text=f"\u2013 {page} \u2013",
                                         x=282.5, y=17.67, width=35, height=12, font_size=12))
        synthetic_pdf = _SyntheticThreePagePdf()
        if straddling_footer_text_object:
            for page in synthetic_pdf.pages:
                page.objects.append(PdfTextObj((291, 29.67, 296, 38.5)))
        if bottom_layout_object:
            for page in synthetic_pdf.pages:
                page.objects.append(_SyntheticLayoutObject((100, 10, 120, 25)))
        if near_footer_layout_object:
            for page in synthetic_pdf.pages:
                page.objects.append(_SyntheticLayoutObject((290, 32, 310, 40)))
        if nearby_pdf_text_object:
            for page in synthetic_pdf.pages:
                page.objects.append(PdfTextObj((295, 33.67, 301, 40)))
        with patch("pypdfium2.PdfDocument", return_value=synthetic_pdf), \
                patch("import_benchmark.extract_text_with_positions", return_value=items):
            result = generate_draft(cases_path, stage, {"2030": source})
        return result

    def test_generate_draft_emits_valid_v1_and_publishes_controlled_fixture(self):
        target = self.root / "integrated-success"
        with staging_directory(target) as stage:
            result = self._generate_fixture(stage)
            staged = json.loads((stage / "draft.json").read_text(encoding="utf-8"))
            validate_v1(staged, artifact_root=stage, check_files=True)
            publish_verified(stage, target)

        published = json.loads((target / "draft.json").read_text(encoding="utf-8"))
        question = published["questions"][0]
        marker_ids = question["extensions"]["paessed.question_number_source_ids"]
        marker = next(obj for obj in published["source_objects"] if obj["id"] == marker_ids[0])
        rendered = next(obj for obj in published["source_objects"]
                        if obj["kind"] == "text_rendering"
                        and obj["id"] != marker_ids[0])

        self.assertEqual(result["questions"], 1)
        self.assertEqual(published["schema_version"], "1.0.0")
        self.assertEqual(question["original_number"], "1")
        self.assertEqual(marker["extensions"]["paessed.metadata_role"], "question_number")
        self.assertEqual(marker["extensions"]["paessed.source_font_size"], 12)
        self.assertEqual(rendered["extensions"]["paessed.effective_font_size"], 12)
        self.assertEqual(rendered["extensions"]["paessed.pdfium_declared_font_size"], 1)
        self.assertEqual(rendered["extensions"]["paessed.pdfium_vertical_scale"], 12)
        self.assertTrue(rendered["extensions"]["paessed.duplicate_of"])
        self.assertEqual(question["extraction_status"], "complete")
        self.assertEqual(published["pages"][0]["source_id"], "2030")
        self.assertEqual(len(published["sources"]), 1)
        validate_v1(published, artifact_root=target, check_files=True)

    def test_generate_draft_excludes_repeated_footer_but_keeps_raw_page_evidence(self):
        target = self.root / "footer-integrated-success"
        with staging_directory(target) as stage:
            result = self._generate_footer_fixture(stage)
            staged = json.loads((stage / "draft.json").read_text(encoding="utf-8"))
            validate_v1(staged, artifact_root=stage, check_files=True)
            publish_verified(stage, target)

        published = json.loads((target / "draft.json").read_text(encoding="utf-8"))
        raw = json.loads((target / "evidence" / "extraction.raw.json").read_text(encoding="utf-8"))
        self.assertEqual(result["questions"], 3)
        for page in (1, 2, 3):
            footer_text = f"\u2013 {page} \u2013"
            question = next(q for q in published["questions"]
                            if q["id"] == f"footer-fixture-page-{page}")
            question_text = [block.get("text") for block in question["stem"] + [
                block for option in question["options"] for block in option["blocks"]
            ] if block.get("type") == "text"]
            self.assertNotIn(footer_text, question_text)
            raw_items = raw["2030"][str(page)]["items"]
            self.assertIn(footer_text, [item["text"] for item in raw_items])
            footer_source_id = next(item["source_id"] for item in raw_items
                                    if item["text"] == footer_text)
            self.assertNotIn(footer_source_id, {entry["id"] for entry in published["source_objects"]})

    def test_generate_draft_keeps_bottom_center_number_near_last_option(self):
        with staging_directory(self.root / "footer-integrated-near-content") as stage:
            self._generate_footer_fixture(stage, nearby_option_marker=True)
            draft = json.loads((stage / "draft.json").read_text(encoding="utf-8"))

        for page in (1, 2, 3):
            footer_text = f"\u2013 {page} \u2013"
            question = next(q for q in draft["questions"]
                            if q["id"] == f"footer-fixture-page-{page}")
            option_d = next(o for o in question["options"] if o["label"] == "D")
            self.assertIn(footer_text, [block.get("text") for block in option_d["blocks"]
                                        if block.get("type") == "text"])

    def test_generate_draft_keeps_layout_object_below_possible_footer(self):
        with staging_directory(self.root / "footer-integrated-layout-content") as stage:
            self._generate_footer_fixture(stage, bottom_layout_object=True)
            draft = json.loads((stage / "draft.json").read_text(encoding="utf-8"))
            raw = json.loads((stage / "evidence" / "extraction.raw.json").read_text(encoding="utf-8"))

        for page in (1, 2, 3):
            question = next(q for q in draft["questions"]
                            if q["id"] == f"footer-fixture-page-{page}")
            raw_id = next(obj["source_id"] for obj in raw["2030"][str(page)]["objects"]
                          if obj["type"] == "_SyntheticLayoutObject")
            self.assertIn(raw_id, {entry["id"] for entry in draft["source_objects"]
                                   if entry["region_id"] == question["region_ids"][0]})
            unresolved_ids = {source_id for block in question["stem"] + [
                block for option in question["options"] for block in option["blocks"]
            ] if block.get("type") == "unresolved" for source_id in block.get("source_ids", [])}
            self.assertIn(raw_id, unresolved_ids)

    def test_generate_draft_excludes_straddling_footer_glyph_but_keeps_raw_evidence(self):
        with staging_directory(self.root / "footer-integrated-glyph") as stage:
            self._generate_footer_fixture(stage, straddling_footer_text_object=True)
            draft = json.loads((stage / "draft.json").read_text(encoding="utf-8"))
            raw = json.loads((stage / "evidence" / "extraction.raw.json").read_text(encoding="utf-8"))

        for page in (1, 2, 3):
            question = next(q for q in draft["questions"]
                            if q["id"] == f"footer-fixture-page-{page}")
            glyph_id = next(obj["source_id"] for obj in raw["2030"][str(page)]["objects"]
                            if obj["type"] == "PdfTextObj"
                            and obj["bbox_ll"] == [291.0, 29.67, 296.0, 38.5])
            self.assertNotIn(glyph_id, {entry["id"] for entry in draft["source_objects"]
                                        if entry["region_id"] == question["region_ids"][0]})
            unresolved_ids = {source_id for block in question["stem"] + [
                block for option in question["options"] for block in option["blocks"]
            ] if block.get("type") == "unresolved" for source_id in block.get("source_ids", [])}
            self.assertNotIn(glyph_id, unresolved_ids)

    def test_generate_draft_keeps_layout_object_inside_extended_footer_margin(self):
        with staging_directory(self.root / "footer-integrated-near-layout") as stage:
            self._generate_footer_fixture(stage, near_footer_layout_object=True)
            draft = json.loads((stage / "draft.json").read_text(encoding="utf-8"))
            raw = json.loads((stage / "evidence" / "extraction.raw.json").read_text(encoding="utf-8"))

        for page in (1, 2, 3):
            question = next(q for q in draft["questions"]
                            if q["id"] == f"footer-fixture-page-{page}")
            footer_id = next(item["source_id"] for item in raw["2030"][str(page)]["items"]
                             if item["text"] == f"\u2013 {page} \u2013")
            layout_id = next(obj["source_id"] for obj in raw["2030"][str(page)]["objects"]
                             if obj["type"] == "_SyntheticLayoutObject"
                             and obj["bbox_ll"] == [290.0, 32.0, 310.0, 40.0])
            region_objects = {entry["id"] for entry in draft["source_objects"]
                              if entry["region_id"] == question["region_ids"][0]}
            self.assertIn(layout_id, region_objects)
            unresolved_ids = {source_id for block in question["stem"] + [
                block for option in question["options"] for block in option["blocks"]
            ] if block.get("type") == "unresolved" for source_id in block.get("source_ids", [])}
            self.assertIn(footer_id, unresolved_ids)
            self.assertIn(layout_id, unresolved_ids)

    def test_generate_draft_does_not_absorb_nearby_pdf_text_into_footer_cutoff(self):
        with staging_directory(self.root / "footer-integrated-near-pdf-text") as stage:
            self._generate_footer_fixture(stage, nearby_pdf_text_object=True)
            draft = json.loads((stage / "draft.json").read_text(encoding="utf-8"))
            raw = json.loads((stage / "evidence" / "extraction.raw.json").read_text(encoding="utf-8"))

        for page in (1, 2, 3):
            question = next(q for q in draft["questions"]
                            if q["id"] == f"footer-fixture-page-{page}")
            page_items = raw["2030"][str(page)]["items"]
            footer_id = next(item["source_id"] for item in page_items
                             if item["text"] == f"\u2013 {page} \u2013")
            nearby_text_id = next(item["source_id"] for item in page_items
                                   if item["text"] == "Texto cercano")
            adjacent_id = next(obj["source_id"] for obj in raw["2030"][str(page)]["objects"]
                               if obj["type"] == "PdfTextObj"
                               and obj["bbox_ll"] == [295.0, 33.67, 301.0, 40.0])
            region_source_ids = {obj["id"] for obj in draft["source_objects"]
                                 if obj["region_id"] == question["region_ids"][0]}
            unresolved_ids = {source_id for block in question["stem"] + [
                block for option in question["options"] for block in option["blocks"]
            ] if block.get("type") == "unresolved"
                              for source_id in block.get("source_ids", [])}

            self.assertEqual(question["extraction_status"], "partial")
            self.assertIn(footer_id, region_source_ids)
            self.assertIn(nearby_text_id, region_source_ids)
            self.assertIn(adjacent_id, region_source_ids)
            self.assertIn(footer_id, unresolved_ids)
            self.assertIn(nearby_text_id, unresolved_ids)

    def test_generate_draft_does_not_publish_tampered_staged_evidence(self):
        target = self.root / "integrated-invalid"
        with self.assertRaisesRegex(DraftContractError, "Missing or changed artifact"):
            with staging_directory(target) as stage:
                self._generate_fixture(stage)
                crop = next((stage / "evidence" / "crops").glob("*.png"))
                crop.write_bytes(b"tampered after generation")
                publish_verified(stage, target)

        self.assertFalse(target.exists())
        self.assertEqual(list(self.root.glob(".integrated-invalid.stage-*")), [])

    def test_generate_draft_does_not_publish_invalid_staged_draft(self):
        target = self.root / "integrated-invalid-draft"
        with self.assertRaisesRegex(DraftContractError, "Unknown region"):
            with staging_directory(target) as stage:
                self._generate_fixture(stage)
                path = stage / "draft.json"
                draft = json.loads(path.read_text(encoding="utf-8"))
                draft["questions"][0]["region_ids"] = ["missing-region"]
                path.write_text(json.dumps(draft), encoding="utf-8")
                publish_verified(stage, target)

        self.assertFalse(target.exists())
        self.assertEqual(list(self.root.glob(".integrated-invalid-draft.stage-*")), [])

    def test_ai_audit_and_blocking_issue_are_retained(self):
        response = {"schema_version": "1.0", "candidate_id": "candidate-a",
                    "action": "replace", "agent": {"cli": "test-cli", "model": "test-model"},
                    "result": {"type": "math", "latex": "2\\cdot3", "display": False,
                               "source_ids": ["atom-math"], "owner": "stem"}}
        event = {"id": "ai-1", "cli": "test-cli", "model": "test-model",
                 "target_id": "candidate-a", "question_id": "q-a", "candidate_type": "math",
                 "evidence_ids": ["ev-a"], "source_ids": ["atom-math"],
                 "action": "replace", "result_type": "math",
                 "validation": "schema_source_owner_revalidated", "response": response,
                 "timestamp": "2026-09-24T12:00:00Z"}
        self.draft["extraction"]["ai_interventions"].append(event)
        self.draft["issues"].append({"id": "issue-a", "code": "MATH_UNPROVEN",
                                     "severity": "warning", "target_id": "q-a",
                                     "region_ids": ["region-a"], "evidence_ids": ["ev-a"],
                                     "message": "Check expression"})
        result = self.assemble()
        self.assertEqual(result["extraction"]["ai_interventions"], [event])
        self.assertTrue(result["issues"][0]["blocks_completion"])
        self.assertEqual(result["questions"][0]["extraction_status"], "partial")

    def test_bad_evidence_hash_and_missing_file_abort(self):
        self.draft["evidence"][0]["path"] = "evidence/missing.png"
        with self.assertRaisesRegex(DraftContractError, "Missing evidence crop"):
            self.assemble()
        self.draft["evidence"][0]["path"] = "evidence/q.png"
        emitted = self.assemble()
        (self.root / "evidence" / "q.png").write_bytes(b"changed")
        with self.assertRaisesRegex(DraftContractError, "Missing or changed artifact"):
            validate_v1(emitted, artifact_root=self.root, check_files=True)

    def test_publication_failure_leaves_existing_output_and_cleans_stage(self):
        target = self.root / "published"
        target.mkdir()
        (target / "historical.txt").write_text("keep", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            with staging_directory(target):
                pass
        self.assertEqual((target / "historical.txt").read_text(encoding="utf-8"), "keep")
        empty_target = self.root / "new"
        with self.assertRaises(OSError):
            with staging_directory(empty_target) as stage:
                draft = self.assemble()
                (stage / "evidence").mkdir()
                (stage / "assets").mkdir()
                (stage / "evidence" / "q.png").write_bytes(b"evidence bytes")
                (stage / "assets" / "graph.png").write_bytes(b"asset bytes")
                (stage / "draft.json").write_text(json.dumps(draft), encoding="utf-8")
                with patch("draft_v1_emitter.os.rename", side_effect=OSError("rename failed")):
                    publish_verified(stage, empty_target)
        self.assertFalse(empty_target.exists())
        self.assertEqual(list(self.root.glob(".new.stage-*")), [])

    def test_source_manifest_uses_explicit_mapping(self):
        manifest = self.root / "sources.json"
        manifest.write_text(json.dumps({"pdf-a": "known.pdf"}), encoding="utf-8")
        self.assertEqual(source_paths_from_manifest(manifest),
                         {"pdf-a": self.root / "known.pdf"})

    def test_duplicate_pdf_hash_cannot_claim_two_sources(self):
        first, second = self.root / "one.pdf", self.root / "two.pdf"
        first.write_bytes(b"same synthetic PDF")
        second.write_bytes(b"same synthetic PDF")
        with patch("pypdfium2.PdfDocument"):
            with self.assertRaisesRegex(ValueError, "Same PDF mapped"):
                source_records({"pdf-a": [{}], "pdf-b": [{}]},
                               {"pdf-a": first, "pdf-b": second},
                               lambda p: digest(p.read_bytes()))

    def test_new_run_discards_stale_object_identity_map(self):
        _SOURCE_IDS[123] = "prior-run:source"
        with self.assertRaises(FileNotFoundError):
            generate_draft(self.root / "missing-cases.json", self.root / "output", {})
        self.assertEqual(_SOURCE_IDS, {})


if __name__ == "__main__":
    unittest.main()
