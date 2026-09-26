import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/paes-importer/scripts'))
import import_benchmark as m

def item(text,x,y,w=15,h=12):
    return SimpleNamespace(text=text,x=x,y=y,width=w,height=h,font_size=12)

class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.anchor=item('8.',30,700)
        m._SOURCE_IDS.clear()

    def classify(self, values):
        return m.question_boundary_candidates(self.anchor,[self.anchor,*values])

    def test_number_at_end_of_answer_is_content(self):
        value=item('44.',310,417.9,20,14.52)
        self.assertEqual(self.classify([item('A)',60,420),item('El total es',80,420,225),value]),([],[]))

    def test_answer_begins_with_number_and_inline_prefix(self):
        values=m.expand_inline_items([self.anchor,item('A) 44.',60,500,60),item('B) 9.',60,450,60)])
        self.assertEqual(m.question_boundary_candidates(values[0],values),([],[]))

    def test_indented_numeric_continuation_stays_with_answer(self):
        self.assertEqual(self.classify([item('A)',60,500),item('44.',90,470)]),([],[]))

    def test_real_aligned_nonconsecutive_heading_with_stem(self):
        heading=item('12.',34,400)
        accepted,ambiguous=self.classify([heading,item('Calcule el valor',65,400,130)])
        self.assertEqual(accepted,[heading]);self.assertEqual(ambiguous,[])

    def test_sequential_number_without_stem_remains_ambiguous(self):
        heading=item('9.',30,400)
        self.assertEqual(self.classify([heading]),([],[heading]))

    def test_internal_indented_enumeration_with_prose_is_not_boundary(self):
        heading=item('1.',100,500)
        self.assertEqual(self.classify([heading,item('Primer paso',130,500,100)]),([],[heading]))

    def test_other_column_does_not_truncate_current_question(self):
        heading=item('9.',330,500)
        self.assertEqual(self.classify([heading,item('Calcule el valor',360,500,130)]),([],[heading]))

    def test_same_margin_number_during_answers_remains_ambiguous(self):
        heading=item('9.',30,450)
        self.assertEqual(self.classify([item('A)',30,500),heading,item('Algo escrito',60,450,100)]),([],[heading]))

    def test_heading_after_complete_answers_at_same_margin(self):
        heading=item('9.',30,400)
        values=[item(label+')',30,650-i*50) for i,label in enumerate('ABCD')]
        self.assertEqual(self.classify(values+[heading,item('Siguiente enunciado',65,400,150)]),([heading],[]))

    def test_no_numeric_boundary_leaves_continuation_evidence_available(self):
        self.assertEqual(self.classify([item('Texto que continua',60,100,180)]),([],[]))

    def test_bare_number_far_in_other_column_is_not_answer_continuation(self):
        number=item('9.',330,400)
        self.assertEqual(self.classify([item('A)',60,500),number]),([],[number]))

    def test_unsplit_inline_heading_in_other_column_remains_ambiguous(self):
        number=item('9. Enunciado en otra columna',330,400,220)
        self.assertEqual(self.classify([number]),([],[number]))

    def test_same_margin_enumeration_after_colon_remains_ambiguous(self):
        number=item('9.',30,600)
        self.assertEqual(self.classify([item('Considere los pasos:',60,630,150),number,item('Primer paso',60,600,100)]),([],[number]))

    def test_restarted_numbering_is_ambiguous_not_silently_accepted(self):
        number=item('1.',30,400)
        self.assertEqual(self.classify([number,item('Nuevo texto',65,400,120)]),([],[number]))

    def test_ambiguous_boundary_blocks_completion_in_published_v1(self):
        import json,tempfile
        from unittest.mock import patch
        from test_draft_v1_emitter import _SyntheticPdf
        from draft_v1_emitter import staging_directory,publish_verified
        pdf=_SyntheticPdf();pdf.page.objects=[]
        values=[self.anchor,item('Enunciado de ejemplo',60,700,180),item('1.',100,600),item('Paso enumerado',130,600,130)]
        for i,label in enumerate('ABCD'):
            values.extend([item(label+')',60,500-i*45),item('Respuesta posible',90,500-i*45,120)])
        for v in values:v.page=1
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'fixture.pdf';source.write_bytes(b'controlled mock')
            cases=root/'cases.json';cases.write_text(json.dumps({'cases':[{'id':'fixture-q8','year':2030,'question':'8','page':1}]}))
            with staging_directory(root/'output') as stage:
                with patch.object(m.pdfium,'PdfDocument',return_value=pdf),patch.object(m,'extract_text_with_positions',return_value=values):
                    m.generate_draft(cases,stage,{'2030':source})
                publish_verified(stage,root/'output')
            draft=json.loads((root/'output/draft.json').read_text(encoding='utf-8'))
            self.assertEqual(draft['questions'][0]['extraction_status'],'partial')
            self.assertEqual([o['label'] for o in draft['questions'][0]['options']],list('ABCD'))
            issue=next(i for i in draft['issues'] if i['code']=='AMBIGUOUS_QUESTION_BOUNDARY')
            self.assertTrue(issue['blocks_completion']);self.assertTrue(issue['evidence_ids'])

if __name__=='__main__':unittest.main()
