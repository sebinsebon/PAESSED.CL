"""Self-contained regression checks for legacy fraction geometry.

Two negative tests cover legacy fallback risks and preserve their candidates:
numeric row values (so banning currency words cannot pass) and a long axis.
"""
import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/paes-importer/scripts'))
import import_benchmark as importer
from structural_fidelity import validate_and_order


def reconstruct(specs, bar, scale=1):
    items = [SimpleNamespace(text=text, x=x*scale, y=y*scale, width=w*scale,
                             height=10*scale, font_size=10*scale,
                             source_id=f'p:text:{i}')
             for i, (text, x, y, w) in enumerate(specs)]
    objects = [{'type': 'PdfObject', 'bbox_ll': [v*scale for v in bar],
                'source_id': 'p:object:0'}]
    before = copy.deepcopy(objects)
    candidates = importer.detect_math_candidates(items, objects)
    blocks = [{'type': 'math', 'latex': c['latex'], 'display': False,
               'source_ids': c['source_ids'], 'owner': 'stem'}
              for c in candidates if c['kind'] == 'fraction']
    result = validate_and_order(blocks, items, objects, 'evidence', importer._source_id)
    assert objects == before
    return result


class LegacyFractionGeometryTests(unittest.TestCase):
    def test_numeric_rows_touching_rule_endpoint_are_not_verified_fractions(self):
        blocks = reconstruct([('315', 180, 104, 30), ('210', 180, 80, 30)],
                             [0, 100, 180.001, 100.5])
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]['type'], 'unresolved')
        self.assertEqual(blocks[0]['source_ids'], ['p:text:0', 'p:text:1', 'p:object:0'])
        self.assertEqual(blocks[0]['candidate_blocks'][0]['latex'], r'\frac{315}{210}')
        self.assertFalse(any(b.get('structural_fidelity', {}).get('status') == 'verified'
                             for b in blocks))

    def test_long_axis_with_displaced_labels_is_not_a_verified_fraction(self):
        blocks = reconstruct([('3', 96, 125, 6), ('X', 115, 88, 8)],
                             [0, 100, 120, 101])
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]['type'], 'unresolved')
        self.assertEqual(blocks[0]['source_ids'], ['p:text:0', 'p:text:1', 'p:object:0'])
        self.assertEqual(blocks[0]['candidate_blocks'][0]['latex'], r'\frac{3}{X}')
        self.assertFalse(any(b.get('structural_fidelity', {}).get('status') == 'verified'
                             for b in blocks))

    def test_wide_numerator_and_narrow_denominator_remain_supported(self):
        # A long bar is not intrinsically invalid; the whole numerator matters.
        blocks = reconstruct([('a+b', 12, 110, 65), ('c', 41.5, 80, 6)],
                             [10, 100, 80, 101])
        self.assertEqual(blocks[0]['latex'], r'\frac{a+b}{c}')
        self.assertEqual(blocks[0]['structural_fidelity']['status'], 'verified')

    def test_centered_legacy_fraction_at_two_scales(self):
        for scale in [1, 2]:
            with self.subTest(scale=scale):
                blocks = reconstruct([('1', 30, 110, 6), ('4', 30, 80, 6)],
                                     [28, 100, 38, 101], scale)
                self.assertEqual(blocks[0]['latex'], r'\frac{1}{4}')
                self.assertEqual(blocks[0]['structural_fidelity']['status'], 'verified')
