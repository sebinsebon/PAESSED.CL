import sys
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "paes-importer" / "scripts"))
import import_benchmark as importer


def item(text, x, y, width=10, height=10, font_size=10):
    return SimpleNamespace(
        text=text,
        x=x,
        y=y,
        width=width,
        height=height,
        font_size=font_size,
    )


class GenericPipelineTests(unittest.TestCase):

    def test_source_inventory_assigns_stable_ids_and_owner(self):
        text_item = item("x", 100, 400, 8, 14)
        vector = {"type": "PdfObject", "bbox_ll": (99, 393, 120, 394)}

        inventory = importer.build_source_inventory(
            "2026-p1", "region-q", "stem", [text_item], [vector]
        )

        self.assertEqual([entry["id"] for entry in inventory], [
            "2026-p1:text:0", "2026-p1:object:0"
        ])
        self.assertTrue(all(entry["owner"] == "stem" for entry in inventory))

    def test_coverage_rejects_unrepresented_pdf_image(self):
        coverage = importer.assess_source_coverage(
            [{"id": "p:object:0", "kind": "visual", "owner": "stem"}],
            [],
            {},
        )

        self.assertFalse(coverage["complete"])
        self.assertEqual(coverage["uncovered"], ["p:object:0"])

    def test_repeated_math_candidates_require_two_consumers(self):
        items = [
            item("2", 100, 500, 8, 14), item("3", 100, 480, 8, 14),
            item("2", 100, 430, 8, 14), item("3", 100, 410, 8, 14),
        ]
        objects = [
            {"type": "PdfObject", "bbox_ll": (99, 493, 120, 494)},
            {"type": "PdfObject", "bbox_ll": (99, 423, 120, 424)},
        ]

        candidates = importer.detect_math_candidates(items, objects)

        self.assertEqual(len(candidates), 2)
        self.assertEqual(len({source for c in candidates for source in c["source_ids"]}), 6)

    def test_ambiguous_visual_association_is_unresolved(self):
        marker = item("[Image: Im99]", 200, 300, 60, 12)
        objects = [
            {"type": "PdfImage", "bbox_ll": (100, 270, 200, 295)},
            {"type": "PdfImage", "bbox_ll": (260, 270, 360, 295)},
        ]

        associations = importer.associate_visual_objects([marker], objects)

        self.assertEqual(associations, {})

    def test_math_inside_option_keeps_option_owner(self):
        option = item("A)", 90, 400, 12, 12)
        numerator = item("2", 120, 400, 8, 14)
        denominator = item("3", 120, 380, 8, 14)
        objects = [{"type": "PdfObject", "bbox_ll": (119, 393, 130, 394)}]

        blocks = importer.reconstruct_generic_blocks(
            [option, numerator, denominator], objects, "evidence-q", {},
            owner="option:A"
        )

        math = next(block for block in blocks if block["type"] == "math")
        self.assertEqual(math["owner"], "option:A")
        self.assertEqual(len(math["source_ids"]), 3)


    def test_radical_candidate_uses_root_glyph_and_radicand_geometry(self):
        items = [
            item("√", 100, 400, 10, 14),
            item("5", 115, 380, 8, 14),
        ]
        objects = [{"type": "PdfObject", "bbox_ll": (110, 393, 135, 394)}]

        candidates = importer.detect_math_candidates(items, objects)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["latex"], r"\sqrt{5}")

    def test_equation_candidate_preserves_all_same_line_operands(self):
        items = [
            item("A", 100, 400, 8, 14),
            item("+", 112, 400, 8, 14),
            item("B", 124, 400, 8, 14),
            item("=", 136, 400, 8, 14),
            item("C", 148, 400, 8, 14),
        ]

        candidates = importer.detect_math_candidates(items, [])

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["kind"], "equation")
        self.assertEqual(candidates[0]["latex"], "A+B=C")

    def test_nested_unresolved_blocks_make_status_partial(self):
        table = {"type": "table", "rows": [{"cells": [{"blocks": [
            {"type": "unresolved", "reason": "ambiguous"}
        ]}]}]}

        self.assertEqual(
            importer.determine_extraction_status(
                "q", [], [table], [], {"complete": True}
            ),
            "partial",
        )

    def test_fraction_candidate_uses_geometry_and_is_atomic(self):
        items = [
            item("t", 118, 491, 6, 14, 14),
            item("900", 118, 471, 21, 14, 14),
        ]
        objects = [{"type": "PdfObject", "bbox_ll": (117.7, 483.9, 140.0, 485.1)}]

        candidates = importer.detect_math_candidates(items, objects)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["latex"], r"\frac{t}{900}")
        self.assertEqual(candidates[0]["kind"], "fraction")

    def test_fraction_candidate_includes_nearby_operands_outside_rule(self):
        items = [
            item("5", 84, 400, 8, 14, 14),
            item("7", 112, 370, 8, 14, 14),
        ]
        objects = [{"type": "PdfObject", "bbox_ll": (100, 385, 108, 386)}]
        importer.assign_source_ids("p", items, objects)

        candidates = importer.detect_math_candidates(items, objects)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["latex"], r"\frac{5}{7}")
        self.assertEqual(
            set(candidates[0]["source_ids"]),
            {"p:text:0", "p:text:1", "p:object:0"},
        )

    def test_fraction_candidate_does_not_absorb_distant_text(self):
        items = [
            item("5", 84, 400, 8, 14, 14),
            item("7", 112, 370, 8, 14, 14),
            item("9", 132, 400, 8, 14, 14),
        ]
        objects = [{"type": "PdfObject", "bbox_ll": (100, 385, 108, 386)}]
        importer.assign_source_ids("p", items, objects)

        candidates = importer.detect_math_candidates(items, objects)

        self.assertEqual(len(candidates), 1)
        self.assertNotIn("p:text:2", candidates[0]["source_ids"])

    def test_fraction_candidate_does_not_absorb_short_prose_or_adjacent_fraction(self):
        items = [
            item("de", 88, 500, 10, 12, 12),
            item("1", 102, 500, 6, 14, 14),
            item("2", 102, 470, 6, 14, 14),
            item("3", 122, 500, 6, 14, 14),
            item("4", 122, 470, 6, 14, 14),
        ]
        objects = [
            {"type": "PdfObject", "bbox_ll": (100, 485, 108, 486)},
            {"type": "PdfObject", "bbox_ll": (120, 485, 128, 486)},
        ]
        importer.assign_source_ids("p", items, objects)

        candidates = importer.detect_math_candidates(items, objects)

        self.assertEqual([candidate["latex"] for candidate in candidates], [
            r"\frac{1}{2}", r"\frac{3}{4}"
        ])
        self.assertNotIn("p:text:0", candidates[0]["source_ids"])

    def test_fraction_candidate_does_not_absorb_external_exponent(self):
        items = [
            item("a", 104, 400, 8, 12, 12),
            item("b", 104, 370, 8, 12, 12),
            item("2", 123, 405, 5, 8, 8),
        ]
        objects = [{"type": "PdfObject", "bbox_ll": (100, 385, 115, 386)}]

        candidates = importer.detect_math_candidates(items, objects)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["latex"], r"\frac{a}{b}")
        self.assertNotIn(items[2], candidates[0]["items"])

    def test_generic_blocks_do_not_leave_fraction_tokens_as_text(self):
        items = [
            item("La expresión es", 90, 500, 80, 10),
            item("t", 180, 491, 6, 14, 14),
            item("900", 180, 471, 21, 14, 14),
        ]
        objects = [{"type": "PdfObject", "bbox_ll": (179.7, 483.9, 202.0, 485.1)}]

        blocks = importer.reconstruct_generic_blocks(items, objects, "evidence-q", {})

        math_block = next(block for block in blocks if block["type"] == "math")
        self.assertEqual(math_block["latex"], r"\frac{t}{900}")
        text = " ".join(block.get("text", "") for block in blocks if block["type"] == "text")
        self.assertNotIn("900", text)

    def test_visual_assets_are_associated_by_marker_position(self):
        marker = item("[Image: Im99]", 100, 300, 60, 12)
        objects = [{"type": "PdfImage", "bbox_ll": (100, 270, 300, 295)}]

        associations = importer.associate_visual_objects([marker], objects)

        self.assertEqual(associations["Im99"][0], 0)

    def test_table_requires_a_demonstrable_grid(self):
        grid = [
            {"type": "PdfObject", "bbox_ll": (100, 300, 200, 301)},
            {"type": "PdfObject", "bbox_ll": (100, 250, 200, 251)},
            {"type": "PdfObject", "bbox_ll": (100, 250, 101, 301)},
            {"type": "PdfObject", "bbox_ll": (150, 250, 151, 301)},
            {"type": "PdfObject", "bbox_ll": (199, 250, 200, 301)},
        ]

        candidate = importer.detect_table_candidate([], grid)

        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["kind"], "table")

    def test_coverage_marks_unclaimed_math_as_incomplete(self):
        items = [item("2", 100, 400, 8, 14), item("3", 100, 380, 8, 14)]
        objects = [{"type": "PdfObject", "bbox_ll": (99, 393, 120, 394)}]

        inventory = importer.build_source_inventory(
            "p", "region-q", "stem", items, objects
        )
        coverage = importer.assess_source_coverage(inventory, [], {})

        self.assertFalse(coverage["complete"])
        self.assertEqual(len(coverage["uncovered"]), 3)


    def test_coverage_rejects_wrong_owner_and_preserves_candidate_type(self):
        inventory = [{
            "id": "p:object:0",
            "kind": "layout",
            "candidate_type": "layout",
            "owner": "option:A",
        }]
        coverage = importer.assess_source_coverage(
            inventory,
            [{
                "type": "text",
                "text": "mis-owned",
                "owner": "stem",
                "source_ids": ["p:object:0"],
            }],
        )

        self.assertFalse(coverage["complete"])
        self.assertEqual(coverage["misowned"], ["p:object:0"])
        self.assertEqual(inventory[0]["candidate_type"], "layout")
        self.assertEqual(inventory[0]["representation"], ["text"])

    def test_generic_blocks_preserve_text_math_text_order(self):
        items = [
            item("La expresion", 90, 500, 72, 10),
            item("2", 170, 500, 8, 14),
            item("3", 170, 480, 8, 14),
            item(" continua", 190, 500, 48, 10),
        ]
        objects = [{"type": "PdfObject", "bbox_ll": (169, 493, 181, 494)}]

        blocks = importer.reconstruct_generic_blocks(items, objects, "evidence-q", {})

        self.assertEqual([block["type"] for block in blocks], ["text", "math", "text"])
        self.assertEqual(blocks[1]["latex"], r"\frac{2}{3}")
        self.assertFalse(blocks[1]["display"])

    def test_math_operand_at_text_boundary_is_split_after_operator(self):
        items = [
            item("modela mediante p = g", 90, 500, 120, 12),
            item("·", 212, 500, 6, 14, 14),
            item("m, tal que g es constante", 220, 500, 130, 12),
        ]

        expanded = importer.expand_inline_items(items)

        self.assertEqual([part.text for part in expanded], [
            "modela mediante p = g", "·", "m", ", tal que g es constante"
        ])

    def test_math_operand_split_does_not_mutilate_hyphenated_prose(self):
        items = [
            item("-", 100, 500, 5, 12),
            item("a, primer caso considerado", 108, 500, 150, 12),
        ]

        expanded = importer.expand_inline_items(items)

        self.assertEqual([part.text for part in expanded], [
            "-", "a, primer caso considerado"
        ])

    def test_multiline_fraction_requires_a_demonstrable_vertical_relation(self):
        items = [
            item("a", 100, 500, 8, 14, 14),
            item("b", 100, 380, 8, 14, 14),
        ]
        objects = [{"type": "PdfObject", "bbox_ll": (99, 465, 110, 466)}]
        importer.assign_source_ids("p", items, objects)

        candidates = importer.detect_math_candidates(items, objects)

        self.assertEqual(candidates, [])
        inventory = importer.build_source_inventory(
            "p", "region-q", "stem", items, objects
        )
        blocks = importer.reconstruct_generic_blocks(
            items, objects, "evidence-q", {}, owner="stem"
        )
        coverage = importer.assess_source_coverage(inventory, blocks)
        self.assertIn("p:object:0", coverage["uncovered"])
        self.assertEqual(
            importer.determine_extraction_status("q", [], blocks, [], coverage),
            "partial",
        )

    def test_multiline_math_keeps_owner_and_source_ids_per_line(self):
        items = [
            item("x", 100, 500, 8, 14, 14),
            item("+", 112, 500, 8, 14, 14),
            item("1", 124, 500, 8, 14, 14),
            item("y", 100, 470, 8, 14, 14),
            item("+", 112, 470, 8, 14, 14),
            item("2", 124, 470, 8, 14, 14),
        ]
        importer.assign_source_ids("p", items, [])

        blocks = importer.reconstruct_generic_blocks(
            items, [], "evidence-q", {}, owner="option:A"
        )

        math_blocks = [block for block in blocks if block["type"] == "math"]
        self.assertEqual([block["latex"] for block in math_blocks], ["x+1", "y+2"])
        self.assertTrue(all(block["owner"] == "option:A" for block in math_blocks))
        self.assertEqual(
            {source_id for block in math_blocks for source_id in block["source_ids"]},
            {f"p:text:{index}" for index in range(6)},
        )

    def test_ambiguous_multiline_candidate_remains_partial(self):
        blocks = [{
            "type": "unresolved",
            "reason": "structural_fidelity_unproven",
            "candidate_type": "math",
            "candidate_id": "math-multiline",
            "continuation_candidate": True,
            "source_ids": ["p:text:0", "p:text:1"],
        }]

        self.assertEqual(
            importer.determine_extraction_status(
                "q", [], blocks, [], {"complete": True}
            ),
            "partial",
        )

    def test_multiline_candidate_crop_covers_all_source_lines(self):
        with tempfile.TemporaryDirectory(prefix="paes-multiline-crop-") as tmp:
            crop_dir = Path(tmp) / "evidence" / "crops"
            crop_dir.mkdir(parents=True)
            rendered = crop_dir / "q-candidate-math-multiline.png"

            def fake_render_slice(*args):
                rendered.write_bytes(b"png")
                return rendered

            block = {
                "type": "unresolved",
                "candidate_id": "math-multiline",
                "source_ids": ["p:text:0", "p:text:1"],
            }
            inventory = [
                {"id": "p:text:0", "bbox": [100, 400, 110, 412]},
                {"id": "p:text:1", "bbox": [100, 380, 110, 392]},
            ]
            evidence = []

            with patch.object(importer, "render_slice", side_effect=fake_render_slice):
                importer.add_ai_evidence_crops(
                    object(), crop_dir, "q", [block], inventory, evidence,
                    "evidence-q", "region-q", 500, 700,
                )

            self.assertEqual(evidence[0]["bbox"], [97.0, 285.0, 113.0, 323.0])
            self.assertEqual(evidence[0]["source_ids"], block["source_ids"])
            self.assertNotEqual(evidence[0]["id"], "evidence-q")

    def test_multiline_expression_becomes_one_unresolved_candidate_with_full_crop(self):
        items = [
            item("2x +", 100, 500, 40, 14, 14),
            item("1 = 7", 100, 480, 40, 14, 14),
        ]
        importer.assign_source_ids("p", items, [])

        blocks = importer.reconstruct_generic_blocks(
            items, [], "evidence-q", {}, owner="stem"
        )
        unresolved = [block for block in blocks if block["type"] == "unresolved"]

        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0]["reason"], "math_reconstruction_pending")
        self.assertEqual(unresolved[0]["candidate_type"], "math")
        self.assertEqual(
            unresolved[0]["source_ids"], ["p:text:0", "p:text:1"]
        )

        with tempfile.TemporaryDirectory(prefix="paes-multiline-positive-") as tmp:
            crop_dir = Path(tmp) / "evidence" / "crops"
            crop_dir.mkdir(parents=True)
            rendered = crop_dir / "q-candidate-multiline.png"

            def fake_render_slice(*args):
                rendered.write_bytes(b"png")
                return rendered

            evidence = []
            inventory = importer.build_source_inventory(
                "p", "region-q", "stem", items, []
            )
            with patch.object(importer, "render_slice", side_effect=fake_render_slice):
                importer.add_ai_evidence_crops(
                    object(), crop_dir, "q", unresolved, inventory, evidence,
                    "evidence-q", "region-q", 500, 700,
                )

            self.assertEqual(evidence[0]["bbox"], [97.0, 183.0, 143.0, 223.0])
            self.assertEqual(evidence[0]["source_ids"], ["p:text:0", "p:text:1"])

    def test_multiline_detector_does_not_group_prose_with_math(self):
        items = [
            item("de x +", 100, 500, 50, 14, 14),
            item("1 = 7", 100, 480, 40, 14, 14),
        ]

        candidates = importer.detect_math_candidates(items, [])

        self.assertFalse(any(candidate["kind"] == "multiline" for candidate in candidates))

    def test_multiline_detector_rejects_independent_unary_minus_equations(self):
        items = [
            item("x = 5", 100, 500, 40, 14, 14),
            item("-2y = 8", 100, 480, 50, 14, 14),
        ]

        candidates = importer.detect_math_candidates(items, [])

        self.assertFalse(any(candidate["kind"] == "multiline" for candidate in candidates))

    def test_multiline_expression_keeps_lines_after_first_equality(self):
        items = [
            item("2x +", 100, 500, 40, 14, 14),
            item("3y =", 100, 480, 40, 14, 14),
            item("12", 100, 460, 20, 14, 14),
        ]
        importer.assign_source_ids("p", items, [])

        blocks = importer.reconstruct_generic_blocks(
            items, [], "evidence-q", {}, owner="stem"
        )
        unresolved = [block for block in blocks if block["type"] == "unresolved"]

        self.assertEqual(len(unresolved), 1)
        self.assertEqual(
            unresolved[0]["source_ids"],
            ["p:text:0", "p:text:1", "p:text:2"],
        )

    def test_multiline_detector_rejects_uppercase_prose_phrase(self):
        items = [
            item("SI x +", 100, 500, 45, 14, 14),
            item("1 = 7", 100, 480, 40, 14, 14),
        ]

        candidates = importer.detect_math_candidates(items, [])

        self.assertFalse(any(candidate["kind"] == "multiline" for candidate in candidates))

    def test_multiline_detector_rejects_separate_uppercase_prose_tokens(self):
        items = [
            item("SI", 100, 500, 14, 14, 14),
            item("x", 118, 500, 8, 14, 14),
            item("+", 130, 500, 8, 14, 14),
            item("1 = 7", 100, 480, 40, 14, 14),
        ]

        candidates = importer.detect_math_candidates(items, [])

        self.assertFalse(any(candidate["kind"] == "multiline" for candidate in candidates))

    def test_table_cell_reconstructs_nested_fraction(self):
        items = [
            item("2", 120, 275, 8, 14),
            item("3", 120, 255, 8, 14),
        ]
        objects = [
            {"type": "PdfObject", "bbox_ll": (100, 240, 160, 241)},
            {"type": "PdfObject", "bbox_ll": (100, 290, 160, 291)},
            {"type": "PdfObject", "bbox_ll": (100, 240, 101, 291)},
            {"type": "PdfObject", "bbox_ll": (159, 240, 160, 291)},
            {"type": "PdfObject", "bbox_ll": (119, 268, 130, 269)},
        ]

        blocks = importer.reconstruct_generic_blocks(items, objects, "evidence-q", {})

        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["type"], "table")
        nested = blocks[0]["rows"][0]["cells"][0]["blocks"]
        self.assertEqual([block["type"] for block in nested], ["math"])
        self.assertEqual(nested[0]["latex"], r"\frac{2}{3}")


    def test_option_assignment_does_not_guess_between_plausible_owners(self):
        markers = [
            item("A)", 90, 400, 12, 12),
            item("B)", 90, 420, 12, 12),
        ]
        shared = item("x", 120, 410, 8, 10)

        members, object_members, ambiguous = importer.assign_exclusive_option_members(
            [*markers, shared], [], markers
        )

        self.assertEqual(members["A"], [markers[0]])
        self.assertEqual(members["B"], [markers[1]])
        self.assertEqual(ambiguous, [shared])


    def test_fraction_preserves_exponents_in_both_sides(self):
        items = [
            item("2", 100, 400, 8, 14, 14),
            item("3", 108, 408, 6, 9, 9),
            item("2", 100, 370, 8, 14, 14),
            item(chr(183), 112, 370, 8, 14, 14),
            item("9", 120, 370, 8, 14, 14),
        ]
        objects = [{"type": "PdfObject", "bbox_ll": (99, 390, 132, 391)}]

        candidates = importer.detect_math_candidates(items, objects)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["latex"], r"\frac{2^{3}}{2\cdot9}")

    def test_adjacent_equations_reconstruct_as_one_system(self):
        items = [
            item("x", 100, 500, 8, 14),
            item("=", 112, 500, 8, 14),
            item("2", 124, 500, 8, 14),
            item("y", 100, 480, 8, 14),
            item("=", 112, 480, 8, 14),
            item("3", 124, 480, 8, 14),
        ]

        candidates = importer.detect_math_candidates(items, [])

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["kind"], "system")
        self.assertEqual(
            candidates[0]["latex"],
            r"\begin{cases}x=2\\y=3\end{cases}",
        )

    def test_equal_formulae_keep_distinct_structural_owners(self):
        first = [item("A", 100, 400, 8, 14), item("=", 112, 400, 8, 14), item("2", 124, 400, 8, 14)]
        second = [item("A", 100, 300, 8, 14), item("=", 112, 300, 8, 14), item("2", 124, 300, 8, 14)]

        first_blocks = importer.reconstruct_generic_blocks(
            first, [], "evidence-q", {}, owner="stem"
        )
        second_blocks = importer.reconstruct_generic_blocks(
            second, [], "evidence-q", {}, owner="option:B"
        )

        first_math = next(block for block in first_blocks if block["type"] == "math")
        second_math = next(block for block in second_blocks if block["type"] == "math")
        self.assertEqual(first_math["latex"], second_math["latex"])
        self.assertEqual(first_math["owner"], "stem")
        self.assertEqual(second_math["owner"], "option:B")


if __name__ == "__main__":
    unittest.main()
