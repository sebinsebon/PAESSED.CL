import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"skills/paes-importer/scripts"))
import import_benchmark as m
from simple_fractions import numeric_glyph_matches, simple_fraction_groups


def fixture(x=100, text=("1", "4"), scale=.75):
    items=[];objects=[]
    for j,(word,y) in enumerate(zip(text,(406,386))):
        items.append(SimpleNamespace(text=word,x=x,y=y-14,width=7,height=14,font_size=14,page=1))
        objects.append({"type":"PdfTextObj","bbox_ll":[x+1,y,x+6,y+10],
                        "pdfium_text":word,"pdfium_matrix":[scale,0,0,scale,x,y],
                        "pdfium_page_rotation":0,"pdfium_nesting_level":0,"pdfium_page_number":1,"font_size":14,
                        "font_size_declared":14/scale,"font_size_vertical_scale":scale})
    objects.append({"type":"PdfObject","bbox_ll":[x,400,x+8,400.75],"pdfium_nesting_level":0,"pdfium_page_number":1,"pdfium_page_rotation":0})
    m.assign_source_ids("p1",items,objects)
    return items,objects


class SimpleFractionTests(unittest.TestCase):
    def setUp(self): m._SOURCE_IDS.clear()

    def test_displaced_em_boxes_use_proven_glyph_geometry(self):
        items,objects=fixture();before=copy.deepcopy(objects)
        self.assertEqual(len(simple_fraction_groups(items,objects)),1)
        self.assertEqual(objects,before)
        self.assertEqual(items[0].y,392)

    def test_different_font_transforms_same_effective_size(self):
        for scale in (.25,.75,1,2):
            items,objects=fixture(scale=scale)
            self.assertEqual(len(simple_fraction_groups(items,objects)),1)

    def test_rotated_sheared_or_unproven_origin_abstains(self):
        for field in ('rotation','shear','origin','font','text','matrix'):
            with self.subTest(field=field):
                items,objects=fixture();o=objects[0]
                if field=='rotation':o['pdfium_page_rotation']=90
                elif field=='shear':o['pdfium_matrix'][2]=.2
                elif field=='origin':o['pdfium_matrix'][5]+=.1
                elif field=='font':o['font_size']=12
                elif field=='text':o['pdfium_text']='7'
                else:del o['pdfium_matrix']
                self.assertEqual(simple_fraction_groups(items,objects),[])

    def test_rounding_is_not_nearest_neighbor(self):
        items,objects=fixture();objects[0]['pdfium_matrix'][5]+=.001
        self.assertEqual(len(simple_fraction_groups(items,objects)),1)
        objects[0]['pdfium_matrix'][5]+=.01
        self.assertEqual(simple_fraction_groups(items,objects),[])

    def test_missing_glyph_and_duplicate_identity_abstain(self):
        for mode in ('missing','duplicate_object','duplicate_token'):
            items,objects=fixture()
            if mode=='missing':objects.pop(0)
            elif mode=='duplicate_object':objects.append(copy.deepcopy(objects[0]))
            else:items.append(copy.copy(items[0]))
            self.assertEqual(simple_fraction_groups(items,objects),[])

    def test_minus_underline_and_table_edges_abstain(self):
        for mode in ('minus','underline','table','inline_minus','duplicate_bar'):
            items,objects=fixture()
            if mode=='minus':items=items[:1];objects.pop(1)
            elif mode=='underline':objects[-1]['bbox_ll'][1:4:2]=[380,380.75]
            elif mode=='table':objects.append({'type':'PdfObject','bbox_ll':[100,370,100.5,430]})
            elif mode=='duplicate_bar':objects.append(copy.deepcopy(objects[-1]))
            else:objects.append({'type':'PdfTextObj','bbox_ll':[115,397,120,407],'pdfium_text':'+'})
            self.assertEqual(simple_fraction_groups(items,objects),[],mode)

    def test_adjacent_fractions_do_not_share_members(self):
        items,objects=fixture();i2,o2=fixture(x=125,text=('2','3'))
        self.assertEqual(len(simple_fraction_groups(items+i2,objects+o2)),2)

    def test_unmatched_visible_digit_blocks_partial_cluster(self):
        items,objects=fixture()
        objects.append({'type':'PdfTextObj','bbox_ll':[101,409,103,412],'pdfium_text':'9'})
        self.assertEqual(simple_fraction_groups(items,objects),[])

    def test_assignment_and_reconstruction_keep_original_ids(self):
        items,objects=fixture()
        marker=SimpleNamespace(text='A)',x=80,y=384,width=12,height=12,font_size=12,page=1)
        m.assign_source_ids('p1',[marker],[])
        before=[list(o['bbox_ll']) for o in objects]
        members,groups,amb=m.assign_exclusive_option_members([marker,*items],objects,[marker])
        self.assertEqual(amb,[])
        blocks=m.reconstruct_generic_blocks(items,groups['A'],'ev',{},owner='option:A')
        maths=[b for b in blocks if b['type']=='math']
        self.assertEqual([b['latex'] for b in maths],[r"\frac{1}{4}"])
        self.assertEqual(set(maths[0]['source_ids']),{m._source_id(i,'text') for i in items}|{o['source_id'] for o in objects})
        self.assertEqual([o['bbox_ll'] for o in objects],before)
        inventory=m.build_source_inventory('p1','r','option:A',items,objects)
        self.assertIn('paessed.pdfium_geometry',inventory[2]['extensions'])

    def test_stem_fraction_and_multidigit_atomic_token(self):
        items,objects=fixture(text=('12','34'))
        blocks=m.reconstruct_generic_blocks(items,objects,'ev',{},owner='stem')
        self.assertEqual([b['latex'] for b in blocks if b['type']=='math'],[r"\frac{12}{34}"])

    def test_cross_page_nested_and_inconsistent_font_are_rejected(self):
        for field,value in [('pdfium_nesting_level',1),('pdfium_page_number',2),('font_size_declared',99)]:
            items,objects=fixture();objects[0][field]=value
            self.assertEqual(simple_fraction_groups(items,objects),[])

    def test_different_axis_scales_with_verified_font(self):
        items,objects=fixture()
        for o in objects[:2]:o['pdfium_matrix'][0]=1.25
        self.assertEqual(len(simple_fraction_groups(items,objects)),1)

    def test_bar_shared_between_two_possible_pairs_is_rejected(self):
        items,objects=fixture()
        extra=copy.copy(items[0]);extra.text='2';extra.y+=2
        glyph=copy.deepcopy(objects[0]);glyph['pdfium_text']='2';glyph['pdfium_matrix'][5]+=2
        glyph['bbox_ll']=[glyph['bbox_ll'][0],408,glyph['bbox_ll'][2],418]
        self.assertEqual(simple_fraction_groups(items+[extra],objects+[glyph]),[])

    def test_cross_option_tokens_do_not_create_proof(self):
        items,objects=fixture()
        marks=[SimpleNamespace(text=label,x=80,y=y,width=12,height=12,font_size=12,page=1)
               for label,y in [('A)',394),('B)',373)]]
        m.assign_exclusive_option_members(items+marks,objects,marks)
        self.assertNotIn('simple_fraction_proof',objects[-1])

    def test_missing_proof_member_is_not_emitted_as_math(self):
        items,objects=fixture()
        group=simple_fraction_groups(items,objects)[0]
        objects[-1]['simple_fraction_proof']=m._simple_fraction_proof(group,'option:A')
        candidates=m.detect_math_candidates(items,objects[1:],owner='option:A')
        self.assertFalse(any(c['kind']=='fraction' and c['latex'] for c in candidates))

    def test_unmatched_neighboring_digit_cannot_be_dropped(self):
        items,objects=fixture()
        objects.append({'type':'PdfTextObj','bbox_ll':[105,406,110,416],'pdfium_text':'9'})
        self.assertEqual(simple_fraction_groups(items,objects),[])

    def test_token_without_glyph_in_numerator_cluster_abstains(self):
        items,objects=fixture()
        extra=copy.copy(items[0]);extra.text='9';extra.x=109
        self.assertEqual(simple_fraction_groups(items+[extra],objects),[])

    def test_zero_width_table_border_abstains(self):
        items,objects=fixture()
        objects.append({'type':'PdfObject','bbox_ll':[100,370,100,430]})
        self.assertEqual(simple_fraction_groups(items,objects),[])

    def test_only_ambiguous_glyph_can_follow_verified_token_owner(self):
        for upper_y,accepted in [(384,True),(374,False)]:
            with self.subTest(upper_y=upper_y):
                items,objects=fixture()
                for i in items:i.y-=40
                for o in objects:
                    o['bbox_ll'][1]-=40;o['bbox_ll'][3]-=40
                    if 'pdfium_matrix' in o:o['pdfium_matrix'][5]-=40
                marks=[SimpleNamespace(text=label,x=80,y=y,width=12,height=12,font_size=12,page=1)
                       for label,y in [('A)',upper_y),('B)',344)]]
                members,owned,amb=m.assign_exclusive_option_members(items+marks,objects,marks)
                self.assertEqual('simple_fraction_proof' in objects[-1],accepted)
                if accepted:
                    self.assertEqual(objects[-1]['simple_fraction_proof']['previous_glyph_owners'],['ambiguous','option:B'])
                    self.assertEqual([o['source_id'] for o in owned['B']],[o['source_id'] for o in objects])
                else:
                    self.assertTrue(any(o is objects[0] for o in owned['A']))

    def test_vertically_adjacent_fractions_use_verified_neighbor_geometry(self):
        items,objects=fixture()
        lower,lower_objects=fixture(text=('2','3'))
        for i in lower:i.y-=40
        for o in lower_objects:
            o['bbox_ll'][1]-=40;o['bbox_ll'][3]-=40
            if 'pdfium_matrix' in o:o['pdfium_matrix'][5]-=40
        self.assertEqual(len(simple_fraction_groups(items+lower,objects+lower_objects)),2)

if __name__=='__main__':unittest.main()
