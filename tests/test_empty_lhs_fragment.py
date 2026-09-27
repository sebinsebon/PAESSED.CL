"""Self-contained checks for fragments whose expression relations are unproven."""
import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/paes-importer/scripts'))
from structural_fidelity import validate_and_order


def fixture(latex, tokens=None, y=100, offset=0):
    items = [SimpleNamespace(text=t, x=20+20*i, y=y, width=18, height=12,
                             font_size=12, source_id=f'p:text:{offset+i}')
             for i, t in enumerate(tokens or [latex])]
    block = dict(type='math', latex=latex, display=True, owner='stem',
                 source_ids=[i.source_id for i in items], evidence_id='evidence')
    return block, items


def gate(blocks, items, objects=None):
    return validate_and_order(blocks, items, objects or [], 'evidence',
                              lambda obj, kind: obj['source_id'] if isinstance(obj, dict) else obj.source_id)


class EmptyLhsFragmentTests(unittest.TestCase):
    def test_empty_lhs_preserves_candidate_and_provenance(self):
        for latex in ['=3', ' =x', '\t  = -2', '=x()']:
            with self.subTest(latex=latex):
                block, items = fixture(latex)
                before = copy.deepcopy(block)
                result = gate([block], items)[0]
                self.assertEqual(result['type'], 'unresolved')
                self.assertEqual(result['candidate_blocks'], [before])
                for key in ['source_ids', 'owner', 'evidence_id']:
                    self.assertEqual(result[key], before[key])
                self.assertEqual(result['structural_fidelity']['status'], 'unresolved')
                self.assertEqual(result['structural_fidelity']['reasons'], ['expression_relations_unproven'])
                self.assertEqual(block, before)

    def test_continuation_remains_separate_without_inventing_relation(self):
        first, a = fixture('x=1+2')
        second, b = fixture('=3', y=70, offset=1)
        original = gate([first], a)[0]
        result = gate([first, second], a+b)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], original)
        self.assertEqual(result[1]['type'], 'unresolved')
        self.assertEqual(result[1]['candidate_blocks'], [second])
        self.assertEqual(result[1]['source_ids'], second['source_ids'])
        self.assertEqual(result[1]['structural_fidelity']['reasons'], ['expression_relations_unproven'])

    def test_preserves_existing_reason_and_glyph_evidence(self):
        block, items = fixture('=3')
        objects = [dict(type='PdfTextObj', bbox_ll=[39, 90, 41, 120], source_id='p:object:0')]
        result = gate([block], items, objects)[0]
        self.assertEqual(result['structural_fidelity']['reasons'],
                         ['untranscribed_grouping_glyph', 'expression_relations_unproven'])
        self.assertEqual(result['source_ids'], ['p:text:0', 'p:object:0'])
        self.assertEqual(result['candidate_blocks'], [block])
        self.assertEqual(result['evidence_id'], 'evidence')

    def test_complete_equations_and_other_expressions_stay_verified(self):
        for latex, tokens in [('f(x)=2x+4', None), ('A+B=C', ['A', '+', 'B', '=', 'C']),
                              ('2+3', None), ('x=1=1', None)]:
            with self.subTest(latex=latex):
                block, items = fixture(latex, tokens)
                result = gate([block], items)[0]
                self.assertEqual(result['latex'], latex)
                self.assertEqual(result['structural_fidelity']['status'], 'verified')
                self.assertEqual(result['structural_fidelity']['reasons'], [])

    def test_rhs_fragment_now_abstains_under_combined_scope(self):
        # Previously excluded from LHS-only work; now covered by RHS abstention.
        block, items = fixture('x4=+()')
        result = gate([block], items)[0]
        self.assertEqual(result['type'], 'unresolved')
        self.assertEqual(result['candidate_blocks'], [block])
        self.assertEqual(result['structural_fidelity']['reasons'], ['expression_relations_unproven'])

    def test_explicit_composites_keep_existing_treatment(self):
        for latex in [r'\begin{aligned}&=3\end{aligned}', r'\begin{cases}=3\end{cases}',
                      r'=3\\x', '=3&x', '=3\nx']:
            with self.subTest(latex=latex):
                block, items = fixture(latex)
                result = gate([block], items)[0]
                reasons = ['system_grouping_requires_evidence'] if r'\begin{cases}' in latex else []
                self.assertEqual(result['structural_fidelity']['reasons'], reasons)
                self.assertEqual(result['structural_fidelity']['status'], 'unresolved' if reasons else 'verified')
                self.assertEqual(result.get('candidate_blocks', [result])[0]['latex'], latex)


if __name__ == '__main__':
    unittest.main()
