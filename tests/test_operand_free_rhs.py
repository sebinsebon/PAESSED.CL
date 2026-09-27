"""RHS abstention fixtures contain no private source data."""
import copy
import unittest
from test_empty_lhs_fragment import fixture, gate


class OperandFreeRhsTests(unittest.TestCase):
    def test_operand_free_rhs_preserves_candidate(self):
        for latex in ['a=+()', 'a=( + )', 'a= \t- ( ) ', 'a=−(())']:
            with self.subTest(latex=latex):
                block, items = fixture(latex)
                before = copy.deepcopy(block)
                result = gate([block], items)[0]
                self.assertEqual(result['type'], 'unresolved')
                self.assertEqual(result['structural_fidelity']['status'], 'unresolved')
                self.assertEqual(result['candidate_blocks'], [before])
                for key in ['source_ids', 'owner', 'evidence_id']:
                    self.assertEqual(result[key], before[key])
                self.assertEqual(result['structural_fidelity']['reasons'], ['expression_relations_unproven'])
                self.assertEqual(block, before)

    def test_existing_reason_and_evidence_survive(self):
        block, items = fixture('a=+()')
        objects = [dict(type='PdfTextObj', bbox_ll=[39, 90, 41, 120], source_id='p:object:0')]
        result = gate([block], items, objects)[0]
        self.assertEqual(result['structural_fidelity']['reasons'],
                         ['untranscribed_grouping_glyph', 'expression_relations_unproven'])
        self.assertEqual(result['source_ids'], ['p:text:0', 'p:object:0'])
        self.assertEqual(result['candidate_blocks'], [block])
        self.assertEqual(result['owner'], block['owner'])
        self.assertEqual(result['evidence_id'], 'evidence')

    def test_operands_and_out_of_scope_notation_keep_prior_behavior(self):
        for latex in ['a=+(b)', 'a=-(-2)', 'a=+((b+c))', 'a=f()',
                      'a=+', 'a=', 'a=()=b', r'\begin{aligned}a&=+()\end{aligned}',
                      r'a=+()\\b', 'a=+()&b', 'a=+()\nb']:
            with self.subTest(latex=latex):
                block, items = fixture(latex)
                result = gate([block], items)[0]
                self.assertEqual(result['type'], 'math')
                self.assertEqual(result['latex'], latex)
                self.assertEqual(result['structural_fidelity']['reasons'], [])
                self.assertEqual(result['structural_fidelity']['status'], 'verified')
        block, items = fixture(r'\begin{cases}a=+()\end{cases}')
        result = gate([block], items)[0]
        self.assertEqual(result['candidate_blocks'], [block])
        self.assertEqual(result['structural_fidelity']['reasons'], ['system_grouping_requires_evidence'])
        self.assertEqual(result['structural_fidelity']['status'], 'unresolved')


if __name__ == '__main__':
    unittest.main()
