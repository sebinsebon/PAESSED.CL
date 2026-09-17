import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/paes-importer/scripts"
sys.path.insert(0, str(SCRIPTS))

from ai_on_demand import apply_ai_response, build_ai_request, validate_ai_response
from import_benchmark import detect_math_candidates, expand_inline_items


class AiOnDemandTests(unittest.TestCase):
    def _draft_and_response_for_apply(self):
        unresolved = {
            "type": "unresolved", "reason": "structural_fidelity_unproven",
            "candidate_id": "math-ab12", "candidate_type": "math",
            "owner": "stem", "source_ids": ["p:text:1"],
            "structural_fidelity": {
                "status": "unresolved", "reasons": ["ambiguous"],
                "source_ids": ["p:text:1"], "representation_type": "unresolved",
                "bbox_ll": [10, 20, 40, 50], "baseline": 20,
            },
        }
        draft = {
            "source_objects": [{
                "id": "p:text:1", "region_id": "region-q", "owner": "stem",
                "kind": "text", "candidate_type": "math", "bbox": [10, 20, 40, 50],
            }],
            "questions": [{
                "id": "q", "region_ids": ["region-q"], "stem": [unresolved],
                "options": [], "extraction_status": "partial",
            }],
            "issues": [], "extraction": {"ai_interventions": []},
        }
        response = {
            "schema_version": "1.0", "candidate_id": "math-ab12", "action": "replace",
            "agent": {"cli": "host-cli", "model": "host-model"},
            "result": {
                "type": "math", "latex": "1+1", "display": False,
                "source_ids": ["p:text:1"], "owner": "stem",
            },
        }
        return draft, response

    def test_simple_arithmetic_tokens_reconstruct_without_solving(self):
        items = [
            SimpleNamespace(text="-", x=0, y=10, width=5, height=12, font_size=12),
            SimpleNamespace(text="32", x=7, y=10, width=12, height=12, font_size=12),
        ]
        candidates = detect_math_candidates(items, [], owner="option:A")
        self.assertEqual([c["latex"] for c in candidates], ["-32"])

    def test_inline_equation_span_is_split_into_text_and_math(self):
        item = SimpleNamespace(
            text="calcula que debe gastar $2600 + $1400 = $4000.",
            x=100, y=10, width=260, height=12, font_size=12,
            source_id="p:text:1",
        )
        parts = expand_inline_items([item])
        self.assertEqual([part.text for part in parts], [
            "calcula que debe gastar ", "$2600 + $1400 = $4000", "."
        ])
        self.assertEqual(parts[1].source_id, "p:text:1#span:1")

    def test_request_contains_only_candidate_crop_context(self):
        candidate = {
            "candidate_id": "math-ab12",
            "candidate_type": "math",
            "owner": "stem",
            "source_ids": ["p:text:1"],
            "ai_evidence_id": "evidence-q-candidate-ab12",
            "structural_fidelity": {"bbox_ll": [10, 20, 40, 50]},
        }
        request = build_ai_request(
            candidate,
            [{"id": "evidence-q-candidate-ab12", "path": "evidence/crops/candidate.png"}],
        )
        self.assertEqual(request["evidence"]["path"], "evidence/crops/candidate.png")
        self.assertNotIn("candidate_blocks", request)
        self.assertNotIn("question_text", request)
        self.assertIn("exactly", request["instruction"])

    def test_response_contract_rejects_answer_like_or_extra_fields(self):
        response = {
            "schema_version": "1.0",
            "candidate_id": "math-ab12",
            "action": "replace",
            "agent": {"cli": "host-cli", "model": "host-model"},
            "result": {
                "type": "math", "latex": "1+1", "display": False,
                "source_ids": ["p:text:1"], "owner": "stem",
                "answer": "2",
            },
        }
        with self.assertRaises(ValueError):
            validate_ai_response(response, {"candidate_id": "math-ab12", "source_ids": ["p:text:1"], "owner": "stem"})

    def test_response_contract_rejects_unescaped_currency_delimiters(self):
        response = {
            "schema_version": "1.0", "candidate_id": "math-ab12", "action": "replace",
            "agent": {"cli": "host-cli", "model": "host-model"},
            "result": {
                "type": "math", "latex": "$2600=2600", "display": False,
                "source_ids": ["p:text:1"], "owner": "stem",
            },
        }
        with self.assertRaises(ValueError):
            validate_ai_response(response, {"candidate_id": "math-ab12", "source_ids": ["p:text:1"], "owner": "stem"})

    def test_apply_replaces_candidate_registers_intervention_and_revalidates(self):
        draft, response = self._draft_and_response_for_apply()
        updated = apply_ai_response(copy.deepcopy(draft), response)
        self.assertEqual(updated["questions"][0]["stem"][0]["type"], "math")
        self.assertEqual(len(updated["extraction"]["ai_interventions"]), 1)
        self.assertEqual(updated["questions"][0]["extraction_status"], "partial")
        self.assertIn("ai_response_requires_revalidation", updated["questions"][0]["stem"][0]["structural_fidelity"]["reasons"])

    def test_generated_issue_for_ambiguous_candidate_is_reconciled_after_replace(self):
        draft, response = self._draft_and_response_for_apply()
        draft["issues"] = [{
            "id": "issue-q-coverage", "code": "AMBIGUOUS_ASSOCIATION",
            "target_id": "q", "blocks_completion": True,
        }]
        updated = apply_ai_response(copy.deepcopy(draft), response)
        self.assertFalse(any(i["code"] == "AMBIGUOUS_ASSOCIATION" for i in updated["issues"]))


if __name__ == "__main__":
    unittest.main()
