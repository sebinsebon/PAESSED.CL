import sys
import json
import shutil
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "paes-importer" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import native_table_hypotheses as native_tables
import import_benchmark as importer


def source(source_id, text, bbox, *, kind="text", source_type=None):
    value = {
        "id": source_id,
        "text": text,
        "bbox": list(bbox),
        "kind": kind,
    }
    if source_type:
        value["type"] = source_type
    return value


Q65_MARKDOWN = """|||Color del vehículo||
|---|---|---|---|
|Tipo de vehículos|Color gris|Color blanco|Total|
|Automóvil|||25|
|Camioneta|Total 20|3|10|
"""


def q65_sources(extra=None):
    values = [
        source("2026-p43:text:6", "Color del vehículo", (285.84, 664.2, 375.12, 676.2)),
        source("2026-p43:text:7", "Tipo de vehículos", (125.4, 641.88, 211.308, 653.88)),
        source("2026-p43:text:8", "Color gris", (252.6, 641.88, 300.948, 653.88)),
        source("2026-p43:text:9", "Color blanco", (352.68, 641.88, 414.96, 653.88)),
        source("2026-p43:text:10", "Total", (476.4, 641.88, 501.648, 653.88)),
        source("2026-p43:text:11", "Automóvil", (142.44, 619.44, 194.496, 631.44)),
        source("2026-p43:text:12", "25", (483.0, 619.44, 495.0, 631.44)),
        source("2026-p43:text:13", "Camioneta", (142.44, 597.12, 194.472, 609.12)),
        source("2026-p43:text:14", "3", (380.76, 597.12, 386.76, 609.12)),
        source("2026-p43:text:15", "10", (483.0, 597.12, 495.0, 609.12)),
        source("2026-p43:text:16", "Total", (192.84, 574.68, 218.088, 586.68)),
        source("2026-p43:text:17", "20", (270.84, 574.68, 282.84, 586.68)),
    ]
    vertical_x = [113.52, 223.56, 330.12, 437.52, 540.6]
    horizontal_y = [564.0, 586.2, 608.52, 630.84, 653.28, 675.6]
    visual_index = 0
    for x in vertical_x:
        for low, high in zip(horizontal_y, horizontal_y[1:]):
            values.append(
                source(
                    f"2026-p43:object:grid-v-{visual_index}",
                    "",
                    (x - 0.24, low, x + 0.24, high),
                    kind="layout",
                    source_type="PdfObject",
                )
            )
            visual_index += 1
    for y in horizontal_y:
        values.append(
            source(
                f"2026-p43:object:grid-h-{visual_index}",
                "",
                (113.52, y - 0.24, 540.6, y + 0.24),
                kind="layout",
                source_type="PdfObject",
            )
        )
        visual_index += 1
    if extra:
        values.extend(extra)
    for value in values:
        value.setdefault("owner", "stem")
    return values


class NativeTableHypothesisTests(unittest.TestCase):
    def build(self, markdown, sources, **kwargs):
        page_number = kwargs.pop("page_number", 43)
        question_id = kwargs.pop("question_id", "q65")
        region_id = kwargs.pop("region_id", "region-q65")
        region_bbox_ll = kwargs.pop("region_bbox_ll", (100, 100, 550, 700))
        return native_tables.build_hypothesis(
            pdf_sha256="pdf-hash",
            pdf_inspector_version="1.20.0",
            page_number=page_number,
            question_id=question_id,
            region_id=region_id,
            region_bbox_ll=region_bbox_ll,
            markdown=markdown,
            source_entries=sources,
            page_has_table=kwargs.pop("page_has_table", True),
            **kwargs,
        )

    def test_q65_preserves_combined_headers_and_empty_cells(self):
        hypothesis = self.build(
            Q65_MARKDOWN,
            [
                source("t1", "Color del vehículo", (200, 640, 300, 650)),
                source("t2", "Tipo de vehículos", (110, 610, 180, 620)),
                source("t3", "Color gris", (200, 610, 250, 620)),
                source("t4", "Color blanco", (300, 610, 370, 620)),
                source("t5", "Total", (450, 610, 480, 620)),
                source("t6", "Automóvil", (110, 580, 180, 590)),
                source("t7", "25", (450, 580, 465, 590)),
                source("t8", "Camioneta", (110, 550, 180, 560)),
                source("t9", "Total 20", (200, 550, 250, 560)),
                source("t10", "3", (300, 550, 315, 560)),
                source("t11", "10", (450, 550, 465, 560)),
                source("v1", "", (100, 540, 550, 542), kind="layout", source_type="PdfObject"),
            ],
        )

        table = hypothesis["tables"][0]
        self.assertEqual(table["columns"], 4)
        self.assertEqual(table["rows"][2], ["Automóvil", "", "", "25"])
        self.assertEqual(table["rows"][0], ["", "", "Color del vehículo", ""])
        self.assertIn("t1", hypothesis["mapped_source_ids"])
        self.assertIn("v1", hypothesis["mapped_source_ids"])
        self.assertEqual(len(hypothesis["mapped_source_ids"]), len(set(hypothesis["mapped_source_ids"])))

    def test_q60_without_demonstrated_table_stays_conservative(self):
        hypothesis = self.build(
            "## 112 118 135 150\n## 151 178 179 192\n",
            [source("t1", "112", (120, 300, 140, 312))],
            page_number=40,
            question_id="q60",
            region_id="region-q60",
            page_has_table=False,
        )

        self.assertEqual(hypothesis["status"], "not_detected")
        self.assertEqual(hypothesis["tables"], [])
        self.assertEqual(hypothesis["mapped_source_ids"], [])
        self.assertEqual(hypothesis["question_status"], "partial")

    def test_table_from_another_question_is_not_assigned(self):
        hypothesis = self.build(
            "|Q29|M|N|\n|---|---|---|\n|3|10|5|\n",
            [source("q30-text", "30", (120, 500, 140, 512))],
            page_number=19,
            question_id="q30",
            region_id="region-q30",
        )

        self.assertEqual(hypothesis["status"], "out_of_region")
        self.assertEqual(hypothesis["mapped_source_ids"], [])
        self.assertNotIn("q30-text", hypothesis["ambiguous_source_ids"])
        self.assertEqual(hypothesis["question_status"], "partial")

    def test_consumed_ids_and_outside_objects_are_not_reused(self):
        hypothesis = self.build(
            "|A|B|\n|---|---|\n|1|2|\n",
            [
                source("inside", "A", (120, 500, 130, 510)),
                source("inside-2", "B", (160, 500, 170, 510)),
                source("outside", "1", (800, 500, 810, 510)),
                source("visual-outside", "", (800, 480, 810, 490), kind="layout", source_type="PdfObject"),
            ],
            consumed_source_ids={"inside"},
        )

        self.assertNotIn("outside", hypothesis["mapped_source_ids"])
        self.assertNotIn("visual-outside", hypothesis["mapped_source_ids"])
        self.assertNotIn("inside", hypothesis["mapped_source_ids"])
        self.assertIn("inside", hypothesis["ambiguous_source_ids"])
        all_ids = hypothesis["mapped_source_ids"] + hypothesis["ambiguous_source_ids"]
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_missing_geometry_blocks_promotion_and_keeps_partial(self):
        hypothesis = native_tables.build_hypothesis(
            pdf_sha256="pdf-hash",
            pdf_inspector_version="1.20.0",
            page_number=43,
            question_id="q65",
            region_id="region-q65",
            region_bbox_ll=None,
            markdown=Q65_MARKDOWN,
            source_entries=[source("t1", "Color del vehículo", (200, 640, 300, 650))],
            page_has_table=True,
        )

        self.assertEqual(hypothesis["status"], "insufficient_geometry")
        self.assertTrue(hypothesis["blocks_completion"])
        self.assertEqual(hypothesis["question_status"], "partial")
        self.assertEqual(hypothesis["mapped_source_ids"], [])

    def test_q65_geometry_resolves_duplicate_total_and_total_20(self):
        hypothesis = native_tables.build_hypothesis(
            pdf_sha256="pdf-hash",
            pdf_inspector_version="1.20.0",
            page_number=43,
            question_id="q65",
            region_id="region-q65",
            region_bbox_ll=(100, 500, 550, 700),
            markdown=Q65_MARKDOWN,
            source_entries=q65_sources(),
            page_has_table=True,
        )

        resolved = native_tables.resolve_table_geometry(
            hypothesis, q65_sources()
        )

        self.assertTrue(resolved["eligible"])
        self.assertEqual(resolved["ambiguous_source_ids"], [])
        self.assertIn("2026-p43:text:10", resolved["mapped_source_ids"])
        self.assertIn("2026-p43:text:16", resolved["mapped_source_ids"])
        self.assertIn("2026-p43:text:17", resolved["mapped_source_ids"])
        self.assertEqual(
            resolved["rows"][-1][0]["source_ids"], ["2026-p43:text:16"]
        )
        self.assertEqual(
            resolved["rows"][-1][1]["source_ids"], ["2026-p43:text:17"]
        )
        self.assertEqual(
            resolved["rows"][0][2]["source_ids"], ["2026-p43:text:6"]
        )

    def test_q65_can_promote_only_after_exact_source_and_visual_coverage(self):
        hypothesis = native_tables.build_hypothesis(
            pdf_sha256="pdf-hash",
            pdf_inspector_version="1.20.0",
            page_number=43,
            question_id="q65",
            region_id="region-q65",
            region_bbox_ll=(100, 500, 550, 700),
            markdown=Q65_MARKDOWN,
            source_entries=q65_sources(),
            page_has_table=True,
        )

        promotion = native_tables.promote_hypothesis(
            hypothesis, q65_sources(), expected_owner="stem"
        )

        self.assertTrue(promotion["eligible"])
        self.assertEqual(promotion["block"]["type"], "table")
        self.assertEqual(len(promotion["block"]["rows"]), 5)
        all_ids = list(promotion["block"]["source_ids"])
        for row in promotion["block"]["rows"]:
            for cell in row["cells"]:
                for nested in cell["blocks"]:
                    all_ids.extend(nested.get("source_ids", []))
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_promotion_rejects_mixed_ownership(self):
        sources = q65_sources()
        next(entry for entry in sources if entry["id"] == "2026-p43:text:17")["owner"] = "option:A"
        hypothesis = native_tables.build_hypothesis(
            pdf_sha256="pdf-hash",
            pdf_inspector_version="1.20.0",
            page_number=43,
            question_id="q65",
            region_id="region-q65",
            region_bbox_ll=(100, 500, 550, 700),
            markdown=Q65_MARKDOWN,
            source_entries=sources,
            page_has_table=True,
        )

        promotion = native_tables.promote_hypothesis(
            hypothesis, sources, expected_owner="stem"
        )

        self.assertFalse(promotion["eligible"])
        self.assertIn("owner_mismatch", promotion["reasons"])

    def test_promotion_rejects_unconsumed_visual_inside_grid(self):
        extra = [
            source(
                "2026-p43:object:unexpected",
                "",
                (250, 570, 260, 580),
                kind="visual",
                source_type="PdfImage",
            )
        ]
        sources = q65_sources(extra)
        hypothesis = native_tables.build_hypothesis(
            pdf_sha256="pdf-hash",
            pdf_inspector_version="1.20.0",
            page_number=43,
            question_id="q65",
            region_id="region-q65",
            region_bbox_ll=(100, 500, 550, 700),
            markdown=Q65_MARKDOWN,
            source_entries=sources,
            page_has_table=True,
        )

        promotion = native_tables.promote_hypothesis(
            hypothesis, sources, expected_owner="stem"
        )

        self.assertFalse(promotion["eligible"])
        self.assertIn("unconsumed_visual_source", promotion["reasons"])
        self.assertIn(
            "2026-p43:object:unexpected", promotion["unresolved_source_ids"]
        )

    def test_q60_never_promotes_to_table(self):
        hypothesis = native_tables.build_hypothesis(
            pdf_sha256="pdf-hash",
            pdf_inspector_version="1.20.0",
            page_number=40,
            question_id="q60",
            region_id="region-q60",
            region_bbox_ll=(100, 100, 550, 700),
            markdown="## 112 118 135 150\n## 151 178 179 192\n",
            source_entries=[],
            page_has_table=False,
        )

        promotion = native_tables.promote_hypothesis(hypothesis, [], expected_owner="stem")

        self.assertFalse(promotion["eligible"])
        self.assertIn("native_table_not_detected", promotion["reasons"])

    def test_real_q65_integration_keeps_coverage_and_fidelity_conservative(self):
        root = Path(__file__).resolve().parents[1]
        draft_path = root / "skills/paes-importer/benchmark/run-holdout-v2-20260918-fixed-v3/draft.json"
        sidecar_path = root / "skills/paes-importer/benchmark/run-holdout-v2-20260918-fixed-v3/evidence/native_table_hypotheses.json"
        if not draft_path.exists() or not sidecar_path.exists():
            self.skipTest("Ensayo 326 integration artifacts are not present")

        with tempfile.TemporaryDirectory(prefix="paes-q65-table-integration-") as temp:
            isolated_path = Path(temp) / "draft.json"
            shutil.copy2(draft_path, isolated_path)
            isolated = json.loads(isolated_path.read_text(encoding="utf-8"))
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            q65 = next(q for q in isolated["questions"] if q["id"] == "holdout-v2-q65")
            q60_before = json.dumps(
                next(q for q in isolated["questions"] if q["id"] == "holdout-v2-q60"),
                sort_keys=True,
            )
            hypothesis = next(
                h for h in sidecar["hypotheses"] if h["question_id"] == "holdout-v2-q65"
            )
            self.assertTrue(hypothesis["promotion"]["eligible"])
            table_block = hypothesis["promotion"]["block_preview"]
            table_ids = set(hypothesis["promotion"]["resolved"]["mapped_source_ids"])

            def block_source_ids(block):
                ids = list(block.get("source_ids", []))
                if block.get("type") == "table":
                    for row in block.get("rows", []):
                        for cell in row.get("cells", []):
                            for nested in cell.get("blocks", []):
                                ids.extend(block_source_ids(nested))
                return ids

            original_stem = list(q65["stem"])
            q65["stem"] = [
                block for block in original_stem
                if not table_ids.intersection(block_source_ids(block))
            ]
            q65["stem"].insert(2, table_block)
            isolated_path.write_text(
                json.dumps(isolated, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            reloaded = json.loads(isolated_path.read_text(encoding="utf-8"))
            q65_reloaded = next(
                q for q in reloaded["questions"] if q["id"] == "holdout-v2-q65"
            )
            inventory = [
                dict(entry) for entry in reloaded["source_objects"]
                if entry.get("region_id") == "region-holdout-v2-q65"
            ]
            blocks = list(q65_reloaded["stem"])
            blocks.extend(
                block for option in q65_reloaded["options"]
                for block in option["blocks"]
            )
            coverage = importer.assess_source_coverage(
                inventory,
                blocks,
                owners={option["id"]: option for option in q65_reloaded["options"]},
            )
            fidelity = importer.fidelity_report(blocks)
            self.integration_metrics = {
                "coverage": coverage,
                "fidelity_failures": len(fidelity["failures"]),
                "remaining_unresolved": sum(
                    block.get("type") == "unresolved" for block in blocks
                ),
            }

            self.assertFalse(coverage["duplicated"])
            self.assertFalse(coverage["misowned"])
            self.assertFalse(coverage["complete"])
            self.assertFalse(fidelity["complete"])
            self.assertFalse(coverage["complete"] and fidelity["complete"])
            self.assertEqual(q65_reloaded["extraction_status"], "partial")
            self.assertEqual(
                q60_before,
                json.dumps(
                    next(q for q in reloaded["questions"] if q["id"] == "holdout-v2-q60"),
                    sort_keys=True,
                ),
            )


if __name__ == "__main__":
    unittest.main()
