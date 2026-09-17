"""Integration regressions: execute the real generic CLI against both PDF sets.

Accepted outcomes are exact structural reconstruction OR an explicit atomic
unresolved candidate with partial status. Oracle helpers are never invoked.
"""
import json
import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/paes-importer/scripts"
sys.path.insert(0, str(SCRIPTS))
from structural_fidelity import fidelity_report
from ai_on_demand import build_ai_request

class GenericDraftFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="paes-fidelity-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.questions = {}
        cls.evidence_by_question = {}
        for name in ("cases", "holdout-cases"):
            out = Path(cls.temp.name) / name
            subprocess.run([sys.executable, "-B", str(SCRIPTS / "import_benchmark.py"),
                            "--cases", str(ROOT / f"skills/paes-importer/benchmark/{name}.json"),
                            "--output", str(out)], check=True, capture_output=True)
            draft = json.loads((out / "draft.json").read_text(encoding="utf-8"))
            cls.questions.update({q["id"]: q for q in draft["questions"]})
            for q in draft["questions"]:
                cls.evidence_by_question[q["id"]] = draft["evidence"]

    def atomic_or_pending(self, q, expected, min_sources=1):
        matches = [b for b in q["stem"] if b["type"]=="math" and b["latex"]==expected]
        if matches:
            self.assertEqual(len(matches),1)
            return matches[0]
        pending = [b for b in q["stem"] if b["type"]=="unresolved"
                   and b.get("reason")=="structural_fidelity_unproven"
                   and len(b.get("source_ids",[]))>=min_sources]
        self.assertEqual(q["extraction_status"], "partial", expected)
        self.assertTrue(pending, expected)
        self.assertTrue(all(b["ai_on_demand"]["status"]=="pending" for b in pending))
        return pending[0]

    def test_p20_actual_inline_order(self):
        q=self.questions["2026-q20"]
        stem=q["stem"]
        index=next(i for i,b in enumerate(stem) if b["type"]=="math")
        self.assertGreater(index,0)
        self.assertEqual(stem[index-1]["type"],"text")
        self.assertIn("valor de", stem[index-1]["text"])
        self.assertEqual(stem[index+1]["type"],"text")
        self.assertIn("?",stem[index+1]["text"])
        self.assertEqual(stem[index]["latex"],r"\frac{2^{3}\cdot3^{4}}{2\cdot9}")
        self.assertFalse(stem[index]["display"])

    def test_p1_simple_arithmetic_is_typed_without_solving(self):
        q=self.questions["2026-q1"]
        stem=q["stem"]
        self.assertEqual(stem[1]["type"], "math")
        self.assertEqual(stem[1]["latex"], "1-(-3)(-2-6)")
        option_math = [
            b["latex"] for option in q["options"] for b in option["blocks"]
            if b["type"]=="math"
        ]
        self.assertEqual(
            [b["latex"] for b in stem if b["type"]=="math"] + option_math,
            ["1-(-3)(-2-6)", "-32", "-23", "-16", "-4"],
        )
        self.assertNotIn("?", stem[1]["latex"])

    def test_p45_full_expression_or_atomic_pending(self):
        q=self.questions["2027-q45"]
        b=self.atomic_or_pending(q,r"\frac{3}{4}\pi\left(\frac{DAP}{2}\right)^{2}",min_sources=7)
        if b["type"]=="unresolved":
            # Include the raised 2 and BOTH fractions in the same candidate.
            self.assertIn("2027-p36:text:8",b["source_ids"])
            self.assertIn("2027-p36:object:7",b["source_ids"])
            self.assertIn("2027-p36:object:12",b["source_ids"])
        self.assertGreater(q["stem"].index(b),0)

    def test_p3_mixed_number_and_order_then_atomic_final_expression(self):
        q=self.questions["2026-q3"]
        stem=q["stem"]
        first=next(i for i,b in enumerate(stem) if b.get("latex")==r"\frac{5}{6}")
        mixed=next(i for i,b in enumerate(stem) if b.get("latex")==r"1\frac{1}{6}")
        self.assertGreater(first,0)
        self.assertIn("n\u00fameros",stem[first-1]["text"])
        self.assertEqual(stem[first+1]["text"],"y")
        self.assertEqual(mixed,first+2)
        self.atomic_or_pending(q,r"3\cdot\left(\frac{1}{6}+\frac{3}{2}\cdot\frac{4}{6}\right)",min_sources=9)

    def test_p4_formulas_follow_introductory_text(self):
        stem=self.questions["2026-q4"]["stem"]
        for latex, intro in [
            (r"\frac{-2(4\cdot5)-(30-2\cdot3)}{12}","expresi\u00f3n"),
            (r"\frac{56}{12}","obteni\u00e9ndose"),
            (r"\frac{14}{3}","obteni\u00e9ndose"),
        ]:
            i=next(i for i,b in enumerate(stem) if b.get("latex")==latex)
            self.assertGreater(i,0)
            self.assertIn(intro,stem[i-1].get("text",""))
            self.assertFalse(stem[i]["display"])

    def test_p9_equations_cannot_remain_ordinary_text(self):
        q=self.questions["2027-q9"]
        equations = [b["latex"] for b in q["stem"] if b["type"]=="math" and "=" in b.get("latex","")]
        self.assertEqual(equations, [
            r"\$2600+\$1400=\$4000", r"3\cdot\$3000=\$9000", r"2\cdot\$2200=\$4400"
        ])
        self.assertFalse(any("=" in b.get("text","") for b in q["stem"] if b["type"]=="text"))

    def test_all_complete_questions_have_structural_proof(self):
        for q in self.questions.values():
            if q["extraction_status"]=="complete":
                with self.subTest(q=q["id"]):
                    blocks=q["stem"]+[b for o in q["options"] for b in o["blocks"]]
                    self.assertTrue(fidelity_report(blocks)["complete"])

    def test_real_p20_reordered_draft_is_rejected(self):
        blocks=copy.deepcopy(self.questions["2026-q20"]["stem"])
        i=next(i for i,b in enumerate(blocks) if b["type"]=="math")
        blocks.insert(0,blocks.pop(i))
        report=fidelity_report(blocks)
        self.assertFalse(report["complete"])
        self.assertTrue(any("reading_order_violation" in f["reasons"] for f in report["failures"]))

    def test_real_p20_demoted_math_is_rejected(self):
        blocks=copy.deepcopy(self.questions["2026-q20"]["stem"])
        b=next(b for b in blocks if b["type"]=="math")
        b["type"]="text"
        b["text"]=b.pop("latex")
        self.assertFalse(fidelity_report(blocks)["complete"])

    def test_real_p45_pending_cannot_be_promoted_by_status_only(self):
        q=self.questions["2027-q45"]
        self.assertFalse(fidelity_report(q["stem"])["complete"])
        from import_benchmark import determine_extraction_status
        self.assertEqual(determine_extraction_status(q["id"],[],q["stem"],q["options"],{"complete":True}),"partial")

    def test_complex_development_candidates_have_minimum_ai_crops(self):
        target_ids = {"2026-q3", "2026-q4", "2026-q35", "2027-q38", "2027-q45"}
        for question_id in target_ids:
            q = self.questions.get(question_id)
            if q is None:
                continue
            candidates = [b for b in q["stem"] + [b for o in q["options"] for b in o["blocks"]]
                          if b["type"]=="unresolved" and b.get("candidate_id")]
            self.assertTrue(candidates, question_id)
            for candidate in candidates:
                request = build_ai_request(candidate, self.evidence_by_question[question_id])
                self.assertEqual(request["candidate_id"], candidate["candidate_id"])
                self.assertNotIn("question_text", request)
                evidence = next(e for e in self.evidence_by_question[question_id]
                                if e['id'] == request['evidence']['id'])
                self.assertEqual(evidence.get('reason'), 'ai_on_demand')
                self.assertEqual(evidence.get('candidate_id'), candidate['candidate_id'])

if __name__=="__main__":
    unittest.main()
