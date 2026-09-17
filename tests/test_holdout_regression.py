
import json
import unittest
import subprocess
import tempfile
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def walk(block):
    yield block
    if block.get("type") == "table":
        for row in block.get("rows", []):
            for cell in row.get("cells", []):
                for nested in cell.get("blocks", []):
                    yield from walk(nested)


class HoldoutRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="paes-holdout-regression-")
        cls.addClassCleanup(cls.temp.cleanup)
        subprocess.run([
            sys.executable, "-B", str(ROOT / "skills/paes-importer/scripts/import_benchmark.py"),
            "--cases", str(ROOT / "skills/paes-importer/benchmark/holdout-cases.json"),
            "--output", cls.temp.name,
        ], check=True, capture_output=True)
        cls.data = json.loads((Path(cls.temp.name) / "draft.json").read_text(encoding="utf-8"))

    def question(self, question_id):
        return next(q for q in self.data["questions"] if q["id"] == question_id)

    def blocks(self, question_id):
        q = self.question(question_id)
        top = q["stem"] + [block for option in q["options"] for block in option["blocks"]]
        return [block for root in top for block in walk(root)]

    def test_p20_exponent_fraction_is_typed_and_complete(self):
        blocks = self.blocks("2026-q20")
        self.assertEqual(self.question("2026-q20")["extraction_status"], "complete")
        self.assertIn(
            r"\frac{2^{3}\cdot3^{4}}{2\cdot9}",
            [block.get("latex") for block in blocks if block.get("type") == "math"],
        )

    def test_p35_unrepresented_objects_force_partial(self):
        blocks = self.blocks("2026-q35")
        self.assertEqual(self.question("2026-q35")["extraction_status"], "partial")
        self.assertGreaterEqual(
            sum(block.get("type") == "unresolved" for block in blocks),
            1,
        )
        self.assertIn(
            ("2026-q35", "STRUCTURAL_COVERAGE_GAP"),
            [(issue["target_id"], issue["code"]) for issue in self.data["issues"]],
        )

    def test_p12_fraction_is_typed_in_generic_output(self):
        blocks = self.blocks("2027-q12")
        self.assertEqual(self.question("2027-q12")["extraction_status"], "complete")
        self.assertIn(
            r"\frac{t}{900}",
            [block.get("latex") for block in blocks if block.get("type") == "math"],
        )

    def test_p45_keeps_expression_candidate_and_visual_asset(self):
        blocks = self.blocks("2027-q45")
        self.assertEqual(self.question("2027-q45")["extraction_status"], "partial")
        pending = next(block for block in blocks if block.get("candidate_type") == "math")
        self.assertEqual(pending["type"], "unresolved")
        self.assertIn("2027-p36:text:8", pending["source_ids"])
        self.assertIn("2027-p36:object:7", pending["source_ids"])
        self.assertIn("2027-p36:object:12", pending["source_ids"])
        self.assertTrue(any(block.get("type") == "image" for block in blocks))

    def test_coverage_created_candidates_keep_geometry(self):
        for question_id in ("2026-q35", "2027-q45"):
            for block in self.blocks(question_id):
                if block.get("reason") == "source_object_unrepresented":
                    proof = block.get("structural_fidelity", {})
                    self.assertIsNotNone(proof.get("baseline"))
                    self.assertTrue(proof.get("bbox_ll"))


if __name__ == "__main__":
    unittest.main()
