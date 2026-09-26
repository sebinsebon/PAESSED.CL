import unittest,sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/paes-importer/scripts'))
import import_benchmark as m

def item(text,x=100,y=400):
    return SimpleNamespace(text=text,x=x,y=y,width=len(text)*6,height=12,font_size=12)

class ArithmeticTests(unittest.TestCase):
    def setUp(self):m._SOURCE_IDS.clear()

    def test_complete_arithmetic_grammar(self):
        for text in ['5 − (−4 − 12) : (−9 + 1)','6:3+1','2 * (-3 + +4)','-2-(-3)','2/3','3,5 + 2,5','1.5 - 2','2(3+4)','1-(-3)(-2-6)']:
            with self.subTest(text=text):self.assertTrue(m.complete_arithmetic(text))

    def test_incomplete_and_implicit_concatenation_rejected(self):
        for text in ['2 +','(2+3','2+3)','2 3+4','--3','2 + ()','2..3 + 4','1e3+2']:
            with self.subTest(text=text):self.assertFalse(m.complete_arithmetic(text))

    def test_hours_ratios_and_prose_are_not_division(self):
        for text in ['20:00','20 : 00','20:00+1','2:3','2:3:4','(2:3)','Hora: 20:00','razón 2:3','Temperatura −3 grados']:
            with self.subTest(text=text):self.assertFalse(m.complete_arithmetic(text))

    def test_signed_number_requires_mathematical_context(self):
        self.assertFalse(m.complete_arithmetic('−3'))
        self.assertTrue(m.complete_arithmetic('−3',signed_number=True))
        self.assertTrue(m.complete_arithmetic('-3.5',signed_number=True))

    def test_full_expression_is_one_math_block_without_evaluation(self):
        text='5 − (−4 − 12) : (−9 + 1)'
        blocks=m.reconstruct_generic_blocks([item(text)],[],'ev',{},owner='stem')
        self.assertEqual([b['type'] for b in blocks],['math'])
        self.assertEqual(blocks[0]['latex'],'5-(−4−12):(−9+1)'.replace('−','-'))

    def test_negative_option_is_math_but_prose_negative_is_not(self):
        blocks=m.reconstruct_generic_blocks([item('−3')],[],'ev',{},owner='option:A')
        self.assertEqual(blocks[0]['type'],'math')
        for owner,values in [('stem',[item('−3')]),('option:A',[item('−3'),item('grados',125)])]:
            candidates=m.detect_math_candidates(values,[],owner=owner)
            self.assertFalse(any(c['kind']=='arithmetic' for c in candidates))

    def test_separate_tokens_cannot_join_into_a_new_number(self):
        candidates=m.detect_math_candidates([item('2',100),item('3+4',109)],[],owner='stem')
        self.assertFalse(any(c['kind']=='arithmetic' for c in candidates))

    def test_syntax_does_not_evaluate_division_by_zero(self):
        self.assertTrue(m.complete_arithmetic('1/(2-2)'))

if __name__=='__main__':unittest.main()
