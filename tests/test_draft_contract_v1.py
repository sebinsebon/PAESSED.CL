"""Synthetic contract tests; no source PDF is opened or imported."""

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/paes-importer/scripts"))
from draft_contract import DraftContractError, read_draft, validate_v1


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fixture(root: Path) -> dict:
    (root / "evidence").mkdir()
    (root / "assets").mkdir()
    (root / "evidence" / "q.png").write_bytes(b"evidence bytes")
    (root / "assets" / "graph.png").write_bytes(b"asset bytes")
    return {
        "schema_version": "1.0.0",
        "sources": [{"id": "pdf-a", "sha256": digest(b"synthetic source A"),
                     "page_count": 12, "origin": None}],
        "extraction": {"status": "complete", "tools": {"pdf-inspector": "test"},
                       "ai_interventions": [], "verification_status": "not_run",
                       "needs_manual_audit": True},
        "pages": [{"id": "page-a-1", "source_id": "pdf-a", "page_number": 1,
                   "width": 600, "height": 800, "rotation": 0,
                   "coordinate_system": "top_left_pdf_points", "transform": [1, 0, 0, 1, 0, 0]}],
        "regions": [{"id": "region-a", "page_id": "page-a-1", "bbox": [10, 20, 200, 300],
                     "kind": "question", "transform": [1, 0, 0, 1, 0, 0]}],
        "assets": [{"asset_id": "graph-a", "path": "assets/graph.png", "mime": "image/png",
                    "width": 10, "height": 10, "sha256": digest(b"asset bytes"),
                    "region_ids": ["region-a"], "source_ids": []}],
        "source_objects": [
            {"id": "atom-math", "region_id": "region-a", "owner": "stem",
             "kind": "text", "candidate_type": "math", "bbox": [10, 500, 100, 550]},
            {"id": "atom-option", "region_id": "region-a", "owner": "option:A",
             "kind": "text", "candidate_type": "text", "bbox": [10, 400, 20, 420]},
            {"id": "atom-option-value", "region_id": "region-a", "owner": "option:A",
             "kind": "text", "candidate_type": "text", "bbox": [25, 400, 40, 420]},
        ],
        "evidence": [{"id": "ev-a", "kind": "crop", "path": "evidence/q.png",
                      "region_ids": ["region-a"], "reason": "audit",
                      "sha256": digest(b"evidence bytes")}],
        "contexts": [],
        "questions": [{"id": "q-a", "original_number": "1", "region_ids": ["region-a"],
                       "context_ids": [],
                       "stem": [{"type": "math", "latex": "2\\cdot3", "display": False,
                                 "source_ids": ["atom-math"], "owner": "stem",
                                 "structural_fidelity": {"status": "verified", "reasons": [],
                                     "source_ids": ["atom-math"], "representation_type": "math",
                                     "method": "synthetic", "baseline": 520,
                                     "bbox_ll": [10, 500, 100, 550]}}],
                       "options": [{"id": "A", "label": "A", "owner": "option:A",
                                    "source_ids": ["atom-option"], "blocks": [
                                        {"type": "text", "text": "6", "source_ids": ["atom-option-value"],
                                         "owner": "option:A", "structural_fidelity": {
                                             "status": "verified", "reasons": [],
                                             "source_ids": ["atom-option-value"],
                                             "representation_type": "text", "method": "synthetic",
                                             "baseline": 410, "bbox_ll": [25, 400, 40, 420]}}]}],
                       "structural_fidelity": {"complete": True, "failures": []},
                       "extraction_status": "complete", "needs_manual_audit": True}],
        "unassigned_fragments": [], "issues": [],
    }


class DraftContractV1Tests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.draft = fixture(self.root)

    def test_single_pdf_complete_without_answer_key(self):
        validate_v1(self.draft, artifact_root=self.root, check_files=True)
        self.assertNotIn("answer_key", self.draft)
        self.assertNotIn("correct_answer", self.draft["questions"][0])
        self.draft["questions"][0]["correct_answer"] = "A"
        with self.assertRaisesRegex(DraftContractError, "Schema"):
            validate_v1(self.draft)

    def test_multiple_pdfs_can_have_the_same_page_number(self):
        d = self.draft
        d["sources"].append({"id": "pdf-b", "sha256": digest(b"synthetic source B"),
                             "page_count": 2})
        d["pages"].append({**d["pages"][0], "id": "page-b-1", "source_id": "pdf-b"})
        d["regions"].append({**d["regions"][0], "id": "region-b", "page_id": "page-b-1"})
        d["source_objects"].append({"id": "atom-b", "region_id": "region-b", "owner": "stem",
                                    "kind": "text", "candidate_type": "text", "bbox": [10, 500, 20, 520]})
        second = copy.deepcopy(d["questions"][0])
        second.update(id="q-b", region_ids=["region-b"], original_number="1")
        second["stem"] = [{"type": "text", "text": "Otro PDF", "source_ids": ["atom-b"],
                           "owner": "stem", "structural_fidelity": {"status": "verified",
                               "reasons": [], "source_ids": ["atom-b"],
                               "representation_type": "text", "method": "synthetic",
                               "baseline": 510, "bbox_ll": [10, 500, 20, 520]}}]
        second["options"] = []
        d["questions"].append(second)
        d["run"] = {"purpose": "benchmark", "selection_sha256": digest(b"eight fixed cases")}
        validate_v1(d)

    def test_question_can_span_pages(self):
        d = self.draft
        d["pages"].append({**d["pages"][0], "id": "page-a-2", "page_number": 2})
        d["regions"].append({**d["regions"][0], "id": "region-a-2", "page_id": "page-a-2"})
        d["questions"][0]["region_ids"].append("region-a-2")
        d["source_objects"].append({"id": "atom-next-page", "region_id": "region-a-2",
                                    "owner": "stem", "kind": "text", "candidate_type": "text",
                                    "bbox": [10, 500, 20, 520]})
        d["questions"][0]["stem"].append({"type": "text", "text": "continúa",
                                           "source_ids": ["atom-next-page"], "owner": "stem",
                                           "structural_fidelity": {"status": "verified", "reasons": [],
                                               "source_ids": ["atom-next-page"],
                                               "representation_type": "text", "method": "synthetic",
                                               "baseline": 510, "bbox_ll": [10, 500, 20, 520]}})
        validate_v1(d)

    def test_question_cannot_span_different_pdfs(self):
        d = self.draft
        d["sources"].append({"id": "pdf-b", "sha256": digest(b"synthetic source B"),
                             "page_count": 2})
        d["pages"].append({**d["pages"][0], "id": "page-b-1", "source_id": "pdf-b"})
        d["regions"].append({**d["regions"][0], "id": "region-b", "page_id": "page-b-1"})
        d["questions"][0]["region_ids"].append("region-b")
        with self.assertRaisesRegex(DraftContractError, "multiple PDFs"):
            validate_v1(d)

    def test_duplicate_physical_page_in_one_source_is_rejected(self):
        self.draft["pages"].append({**self.draft["pages"][0], "id": "other-id"})
        with self.assertRaisesRegex(DraftContractError, "Duplicate or out-of-range"):
            validate_v1(self.draft)

    def test_image_asset_and_file_hash(self):
        d = self.draft
        d["source_objects"].append({"id": "atom-image", "region_id": "region-a",
                                    "owner": "stem", "kind": "visual", "candidate_type": "visual",
                                    "bbox": [10, 500, 20, 520]})
        d["questions"][0]["stem"].append({"type": "image", "asset_id": "graph-a",
                                           "source_ids": ["atom-image"], "owner": "stem",
                                           "structural_fidelity": {"status": "verified", "reasons": [],
                                               "source_ids": ["atom-image"],
                                               "representation_type": "image", "method": "synthetic",
                                               "baseline": 500, "bbox_ll": [10, 500, 20, 520]}})
        validate_v1(d, artifact_root=self.root, check_files=True)
        (self.root / "assets" / "graph.png").write_bytes(b"changed")
        with self.assertRaisesRegex(DraftContractError, "changed artifact"):
            validate_v1(d, artifact_root=self.root, check_files=True)

    def test_structural_validation_does_not_touch_artifact_files(self):
        with patch.object(Path, "is_symlink", side_effect=AssertionError("disk access")):
            validate_v1(self.draft)

    def test_references_and_duplicate_ids_are_rejected(self):
        d = copy.deepcopy(self.draft)
        d["regions"][0]["page_id"] = "missing"
        with self.assertRaisesRegex(DraftContractError, "Unknown page"):
            validate_v1(d)
        d = copy.deepcopy(self.draft)
        d["pages"].append(copy.deepcopy(d["pages"][0]))
        with self.assertRaisesRegex(DraftContractError, "Duplicate page ID"):
            validate_v1(d)

    def test_math_requires_latex_and_display(self):
        d = self.draft
        del d["questions"][0]["stem"][0]["latex"]
        with self.assertRaisesRegex(DraftContractError, "Schema"):
            validate_v1(d)

    def test_complete_math_needs_verified_structural_proof(self):
        d = copy.deepcopy(self.draft)
        del d["questions"][0]["stem"][0]["structural_fidelity"]
        with self.assertRaisesRegex(DraftContractError, "Structural fidelity failed"):
            validate_v1(d)
        d = copy.deepcopy(self.draft)
        d["questions"][0]["stem"][0]["structural_fidelity"]["status"] = "unresolved"
        with self.assertRaisesRegex(DraftContractError, "Unproven complete"):
            validate_v1(d)

    def test_recomputed_fidelity_rejects_math_demoted_to_text(self):
        d = self.draft
        block = d["questions"][0]["stem"][0]
        block["type"] = "text"
        block["text"] = "2⋅3"
        del block["latex"]
        del block["display"]
        block["structural_fidelity"]["representation_type"] = "text"
        with self.assertRaisesRegex(DraftContractError, "Structural fidelity failed"):
            validate_v1(d)

    def test_math_delimiters_and_proof_sources_are_checked(self):
        d = copy.deepcopy(self.draft)
        d["questions"][0]["stem"][0]["latex"] = "$2+3$"
        with self.assertRaisesRegex(DraftContractError, "dollar delimiter"):
            validate_v1(d)
        d = copy.deepcopy(self.draft)
        d["questions"][0]["stem"][0]["structural_fidelity"]["source_ids"] = []
        with self.assertRaisesRegex(DraftContractError, "proof source IDs"):
            validate_v1(d)

    def test_complete_rejects_unresolved_and_blocking_issue(self):
        d = copy.deepcopy(self.draft)
        d["questions"][0]["stem"][0] = {"type": "unresolved", "reason": "math_pending",
                                           "evidence_id": "ev-a", "source_ids": ["atom-math"]}
        with self.assertRaisesRegex(DraftContractError, "Unproven complete"):
            validate_v1(d)
        d = copy.deepcopy(self.draft)
        d["issues"].append({"id": "issue-1", "code": "MATH_PENDING", "severity": "warning",
                            "target_id": "q-a", "region_ids": ["region-a"],
                            "message": "pending", "blocks_completion": True})
        with self.assertRaisesRegex(DraftContractError, "Unproven complete"):
            validate_v1(d)

    def test_partial_keeps_unresolved_and_ai_proposals(self):
        d = self.draft
        d["questions"][0]["extraction_status"] = "partial"
        d["questions"][0]["structural_fidelity"] = {"complete": False, "failures": [{}]}
        d["extraction"]["status"] = "partial"
        d["questions"][0]["stem"][0] = {
            "type": "unresolved", "reason": "structural_fidelity_unproven",
            "evidence_id": "ev-a", "ai_evidence_id": "ev-a", "source_ids": ["atom-math"],
            "candidate_id": "candidate-a", "candidate_type": "math",
            "candidate_blocks": [{"type": "math", "latex": "2\\cdot3", "display": False}],
            "ai_on_demand": {"status": "pending", "task": "transcribe_expression_and_relations"},
        }
        validate_v1(d)

    def test_complete_rejects_missing_or_duplicate_source_consumption(self):
        d = copy.deepcopy(self.draft)
        d["questions"][0]["stem"][0]["source_ids"] = []
        d["questions"][0]["stem"][0]["structural_fidelity"]["source_ids"] = []
        with self.assertRaisesRegex(DraftContractError, "Unproven complete"):
            validate_v1(d)
        d = copy.deepcopy(self.draft)
        d["questions"][0]["stem"].append(copy.deepcopy(d["questions"][0]["stem"][0]))
        with self.assertRaisesRegex(DraftContractError, "source coverage"):
            validate_v1(d)

    def test_path_traversal_and_unknown_version_are_rejected(self):
        d = copy.deepcopy(self.draft)
        d["assets"][0]["path"] = "assets/../private.pdf"
        with self.assertRaisesRegex(DraftContractError, "Unsafe assets path"):
            validate_v1(d)
        d = copy.deepcopy(self.draft)
        d["assets"][0]["path"] = "assets/./graph.png"
        with self.assertRaisesRegex(DraftContractError, "Unsafe assets path"):
            validate_v1(d)
        d = copy.deepcopy(self.draft)
        d["schema_version"] = "2.0.0"
        with self.assertRaisesRegex(DraftContractError, "Schema"):
            validate_v1(d)

    def test_context_and_fragment_references_are_checked(self):
        d = copy.deepcopy(self.draft)
        d["contexts"] = [{"id": "ctx", "region_ids": ["region-a"], "blocks": []}]
        d["questions"][0]["context_ids"] = ["ctx"]
        d["unassigned_fragments"] = [{"id": "fragment", "region_ids": ["region-a"],
                                      "blocks": [], "reason": "ambiguous"}]
        with self.assertRaisesRegex(DraftContractError, "Unproven shared context"):
            validate_v1(d)
        d["questions"][0]["extraction_status"] = "partial"
        d["extraction"]["status"] = "partial"
        validate_v1(d)
        d["contexts"][0]["region_ids"] = ["missing"]
        with self.assertRaisesRegex(DraftContractError, "Unknown region"):
            validate_v1(d)

    def test_verified_shared_context_can_support_complete(self):
        d = self.draft
        d["regions"].append({**d["regions"][0], "id": "region-context"})
        d["source_objects"].append({"id": "atom-context", "region_id": "region-context",
                                    "owner": "context:ctx", "kind": "text",
                                    "candidate_type": "text", "bbox": [10, 600, 100, 620]})
        d["contexts"] = [{"id": "ctx", "region_ids": ["region-context"],
                          "blocks": [{"type": "text", "text": "Lee el gráfico",
                                      "source_ids": ["atom-context"], "owner": "context:ctx",
                                      "structural_fidelity": {"status": "verified", "reasons": [],
                                          "source_ids": ["atom-context"],
                                          "representation_type": "text", "method": "synthetic",
                                          "baseline": 610, "bbox_ll": [10, 600, 100, 620]}}]}]
        d["questions"][0]["context_ids"] = ["ctx"]
        validate_v1(d)

    def test_ai_event_preserves_embedded_response_and_source_ids(self):
        d = self.draft
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
        d["extraction"]["ai_interventions"].append(event)
        validate_v1(d)
        event["source_ids"] = ["atom-option"]
        with self.assertRaisesRegex(DraftContractError, "AI event and response disagree"):
            validate_v1(d)

    def test_legacy_draft_is_read_only_and_not_revalidated_as_v1(self):
        path = self.root / "draft.json"
        original = b'{"schema_version":"0.1.0","document":{"sha256":{"2026":"legacy"}}}'
        path.write_bytes(original)
        self.assertEqual(read_draft(path)["schema_version"], "0.1.0")
        self.assertEqual(path.read_bytes(), original)
        existing = (Path(__file__).resolve().parents[1] /
                    "skills/paes-importer/benchmark/run-holdout-v4-matematica-1-20260920-baseline/draft.json")
        before = digest(existing.read_bytes())
        self.assertEqual(read_draft(existing)["schema_version"], "0.1.0")
        self.assertEqual(digest(existing.read_bytes()), before)


if __name__ == "__main__":
    unittest.main()
