import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "paes-importer" / "scripts"))
import import_benchmark as importer


class MathReconstructionTests(unittest.TestCase):
    def test_q4_keeps_the_whole_numerator_over_12(self):
        blocks = importer.reconstruct_q4_stem("evidence-q4", {})
        latex = [block["latex"] for block in blocks if block["type"] == "math"]
        self.assertIn(r"\frac{-2(4\cdot5)-(30-2\cdot3)}{12}", latex)
        self.assertIn(r"\frac{(-8)\cdot(-10)-(30-2\cdot3)}{12}", latex)
        self.assertNotIn(r"-2(4\cdot5)-\frac{30-2\cdot3}{12}", latex)

    def test_q4_preserves_text_math_text_order(self):
        blocks = importer.reconstruct_q4_stem("evidence-q4", {})
        initial = blocks[:3]
        self.assertEqual([block["type"] for block in initial], ["text", "math", "text"])
        self.assertIn("valor de la", initial[0]["text"])
        self.assertEqual(initial[1]["latex"], r"\frac{-2(4\cdot5)-(30-2\cdot3)}{12}")
        self.assertIn("se realizan", initial[2]["text"])

    def test_q3_reconstructs_fraction_and_grouping_math(self):
        blocks = importer.reconstruct_q3_stem("evidence-q3", {})
        latex = [block["latex"] for block in blocks if block["type"] == "math"]
        self.assertIn(r"\frac{5}{6}", latex)
        self.assertIn(r"1\frac{1}{6}", latex)
        self.assertIn(r"3\cdot\left(\frac{1}{6}+\frac{3}{2}\cdot\frac{4}{6}\right)", latex)
        self.assertTrue(all("$" not in value for value in latex))

    def test_q4_display_flags_follow_source_position(self):
        blocks = importer.reconstruct_q4_stem("evidence-q4", {})
        by_latex = {
            block["latex"]: block["display"]
            for block in blocks
            if block["type"] == "math"
        }
        self.assertFalse(by_latex[r"\frac{-2(4\cdot5)-(30-2\cdot3)}{12}"])
        self.assertFalse(by_latex[r"-2(4\cdot5)"])
        self.assertFalse(by_latex[r"(-8)\cdot(-10)"])
        self.assertFalse(by_latex[r"30-2\cdot3"])
        self.assertTrue(by_latex[r"\frac{(-8)\cdot(-10)-(30-2\cdot3)}{12}"])
        self.assertTrue(by_latex[r"\frac{(-8)\cdot(-10)-24}{12}"])
        self.assertTrue(by_latex[r"\frac{56}{12}"])
        self.assertTrue(by_latex[r"\frac{14}{3}"])

    def test_visual_fallback_does_not_make_complete_content_partial(self):
        fallback = importer.determine_extraction_status(
            "q2",
            [{
                "target_id": "q2",
                "code": "TABLE_VISUAL_FALLBACK",
                "blocks_completion": False,
            }],
            [{"type": "image", "asset_id": "asset-q2"}],
            [{"blocks": [{"type": "text", "text": "A"}]}],
        )
        self.assertEqual(fallback, "complete")


    def test_extraction_status_is_independent_from_manual_audit(self):
        complete = importer.determine_extraction_status(
            "q1",
            [],
            [{"type": "text", "text": "ok"}],
            [{"blocks": [{"type": "text", "text": "A"}]}],
        )
        partial_issue = importer.determine_extraction_status(
            "q2",
            [{"target_id": "q2", "code": "UNRESOLVED_TABLE"}],
            [{"type": "text", "text": "ok"}],
            [{"blocks": [{"type": "text", "text": "A"}]}],
        )
        partial_pending = importer.determine_extraction_status(
            "q3",
            [],
            [{"type": "unresolved"}],
            [],
        )
        failed = importer.determine_extraction_status("q4", [], [], [])
        self.assertEqual(complete, "complete")
        self.assertEqual(partial_issue, "partial")
        self.assertEqual(partial_pending, "partial")
        self.assertEqual(failed, "failed")


if __name__ == "__main__":
    unittest.main()
