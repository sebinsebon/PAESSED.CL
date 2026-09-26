"""Operand-free equation LHS checks; other mathematical mechanisms deferred."""
import unittest
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/paes-importer/scripts'))
from math_syntax import math_syntax_failure
from structural_fidelity import validate_and_order
from draft_contract import DraftContractError, validate_v1
from test_draft_contract_v1 import fixture


def gate(latex, owner='stem'):
    # Self-contained fixture: the future-regression file stays untracked.
    items = [SimpleNamespace(text=latex, x=20, y=100, width=80,
                             height=12, font_size=12, source_id='p:text:0')]
    block = {'type': 'math', 'latex': latex, 'display': False,
             'owner': owner, 'source_ids': ['p:text:0']}
    return validate_and_order([block], items, [], 'evidence',
                              lambda item, kind: item.source_id)


class MathSyntaxTests(unittest.TestCase):
    def test_operand_free_grouping_and_signs(self):
        for text in ['()=-x', '( ) = -y', '(())=z', '-(+)=a', '((=b']:
            with self.subTest(text=text):
                self.assertEqual(math_syntax_failure(text), 'equation_lhs_missing_operand')

    def test_no_claim_about_other_notation_or_deferred_mechanisms(self):
        for text in ['(x)=-y', '(-x)=y', 'f()=x', 'f(x)=2x+4',
                     r'\frac{x+1}{y}', '=x()', 'x4=+()', '=-x6()', '()']:
            with self.subTest(text=text):
                self.assertIsNone(math_syntax_failure(text))

    def test_demoted_candidates_keep_content_ids_and_provenance(self):
        for owner in ['option:B', 'option:C']:
            block = gate('()=-x', owner)[0]
            self.assertEqual(block['type'], 'unresolved')
            self.assertEqual(block['source_ids'], ['p:text:0'])
            self.assertEqual(block['owner'], owner)
            self.assertEqual(block['evidence_id'], 'evidence')
            self.assertEqual(block['candidate_blocks'][0]['latex'], '()=-x')
            self.assertIn('equation_lhs_missing_operand', block['structural_fidelity']['reasons'])
            self.assertEqual(block['structural_fidelity']['status'], 'unresolved')

    def test_valid_algebra_keeps_verified_status(self):
        for latex in ['f(x)=2x+4', '(x)=-y', '2x+1=5', '5-(-4-12):(-9+1)']:
            self.assertEqual(gate(latex)[0]['structural_fidelity']['status'], 'verified')

    def test_contract_rejects_invalid_verified_lhs_in_partial_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            draft = fixture(Path(tmp))
            question = draft['questions'][0]
            question['extraction_status'] = 'partial'
            question['structural_fidelity']['complete'] = False
            draft['extraction']['status'] = 'partial'
            validate_v1(draft)
            question['stem'][0]['latex'] = '()=-x'
            with self.assertRaisesRegex(DraftContractError, 'equation_lhs_missing_operand'):
                validate_v1(draft)
