import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "paes-importer" / "scripts"))
import import_benchmark as importer


class RemainingBenchmarkTests(unittest.TestCase):
    def test_q9_reconstructs_table_and_inline_equations(self):
        blocks = importer.reconstruct_q9_stem("evidence-q9", {})
        table = next(block for block in blocks if block["type"] == "table")
        self.assertEqual(len(table["rows"]), 5)
        half_liter = table["rows"][2]["cells"][0]["blocks"]
        self.assertEqual(
            [block["type"] for block in half_liter],
            ["math", "text"],
        )
        self.assertEqual(half_liter[0]["latex"], r"\frac{1}{2}")
        equations = [
            block["latex"]
            for block in blocks
            if block["type"] == "math"
        ]
        self.assertIn(r"\$2600+\$1400=\$4000", equations)
        self.assertIn(r"3\cdot\$3000=\$9000", equations)
        self.assertTrue(all(block["display"] is False for block in blocks if block["type"] == "math"))

    def test_q16_reconstructs_source_table(self):
        blocks = importer.reconstruct_q16_stem("evidence-q16", {})
        table = next(block for block in blocks if block["type"] == "table")
        self.assertEqual(len(table["rows"]), 5)
        self.assertEqual(table["rows"][1]["cells"][0]["blocks"][0]["text"], "Lentejas (L)")
        self.assertEqual(table["rows"][1]["cells"][1]["blocks"][0]["text"], "20 %")

    def test_visual_asset_bbox_can_avoid_label_padding(self):
        region = importer.asset_region(
            (108.058, 268.899, 289.478, 377.891),
            612.0,
            792.0,
            padding_x=0.0,
        )
        self.assertEqual(region[0], 108.06)
        self.assertEqual(region[2], 289.48)


    def test_visual_objects_are_ordered_by_row_then_column(self):
        objects = [
            {"bbox_ll": [108.0, 268.899, 289.5, 377.891]},
            {"bbox_ll": [361.0, 269.317, 542.4, 377.892]},
            {"bbox_ll": [108.0, 85.126, 289.5, 194.215]},
            {"bbox_ll": [361.0, 85.039, 542.4, 194.214]},
        ]
        ordered = importer.order_visual_objects(objects)
        self.assertEqual([round(item["bbox_ll"][0]) for item in ordered], [108, 361, 108, 361])


    def test_q38_reconstructs_inline_formula_and_units(self):
        blocks = importer.reconstruct_q38_stem(
            "evidence-q38",
            {"Im19": "asset-2027-q38-graphic"},
        )
        latex = [block["latex"] for block in blocks if block["type"] == "math"]
        self.assertIn(r"p=g\cdot m", latex)
        self.assertIn(r"3{,}7\ \frac{\mathrm{m}}{\mathrm{s}^2}", latex)
        self.assertIn(r"10\ \frac{\mathrm{m}}{\mathrm{s}^2}", latex)
        self.assertTrue(all(block["display"] is False for block in blocks if block["type"] == "math"))
        self.assertIn(
            {"type": "image", "asset_id": "asset-2027-q38-graphic"},
            blocks,
        )


if __name__ == "__main__":
    unittest.main()
