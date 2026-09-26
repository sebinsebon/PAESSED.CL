"""Visual candidate evidence and containment regressions.

Geometry transcribed from comparative-audit-20260926T162412Z (ec56c3b5),
Matematica (2) Q38/Q47. No PDF, raster, or private artifact is required.
The candidate-link and dangling-reference tests require inspectable evidence,
NOT restored image blocks or a claim that a composite figure is reconstructed.
"""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/paes-importer/scripts'))
import import_benchmark as importer
from draft_contract import DraftContractError, validate_v1
from structural_fidelity import fidelity_report
from test_draft_contract_v1 import fixture


# source_bbox is top-left page geometry, as stored in assets, not PDFium LL.
Q38 = {
    4: [349.8, 149.64, 371.16, 162.72],  # label 4 plus line fragment
    7: [368.28, 136.92, 392.64, 153.24],  # label f plus line fragment
}
Q47 = {
    1: [158.16, 278.28, 209.64, 322.68],
    2: [210.6, 208.56, 279.6, 270.36],
    3: [280.32, 278.28, 357.96, 348.84],
    4: [358.68, 147.24, 488.64, 270.0],
    5: [141.24, 264.96, 168.72, 299.28],  # P; repeats square corner
    6: [485.76, 264.96, 513.24, 299.28],  # T
    7: [206.52, 275.88, 233.88, 310.08],  # Q
    8: [271.68, 257.76, 327.0, 292.08],  # R
    9: [354.96, 274.32, 382.32, 308.52],  # S
}


def crops(boxes):
    blocks = [{'type': 'image', 'asset_id': f'crop-{i}', 'owner': 'stem',
               'source_ids': [f'page:text:{i}', f'page:object:{i}']}
              for i in boxes]
    assets = {f'crop-{i}': {'source_bbox': box, 'source_type': 'rendered_slice',
                          'region_ids': ['region']} for i, box in boxes.items()}
    return blocks, assets


class VisualOverlapRegressionTests(unittest.TestCase):
    def check_candidate_links(self, boxes):
        blocks, assets = crops(boxes)
        original = copy.deepcopy((blocks, assets))
        result = importer.coalesce_visual_crops(blocks, assets, 'evidence')
        self.assertEqual(len(result), len(blocks))
        for before, after in zip(blocks, result):
            self.assertEqual(after['type'], 'unresolved')
            self.assertEqual(after['reason'], 'visual_overlap_unproven')
            self.assertEqual(after['source_ids'], before['source_ids'])
            self.assertEqual(after['owner'], before['owner'])
            self.assertEqual(after['evidence_id'], 'evidence')
            self.assertNotEqual(after.get('structural_fidelity', {}).get('status'), 'verified')
            self.assertEqual(after.get('asset_id'), before['asset_id'],
                             'An unresolved crop must remain directly inspectable')
        self.assertEqual((blocks, assets), original)
        self.assertFalse(fidelity_report(result)['complete'])

    def test_q38_legitimate_labels_keep_candidate_asset_links(self):
        self.check_candidate_links(Q38)

    def test_q47_squares_and_labels_keep_candidate_asset_links(self):
        self.check_candidate_links(Q47)

    def test_uncertain_geometry_preserves_sources_and_assets_without_promotion(self):
        for boxes in [Q38, Q47]:
            blocks, assets = crops(boxes)
            original = copy.deepcopy((blocks, assets))
            result = importer.coalesce_visual_crops(blocks, assets, 'evidence')
            self.assertEqual((blocks, assets), original)
            self.assertEqual([b['source_ids'] for b in result], [b['source_ids'] for b in blocks])
            self.assertTrue(all(b['type'] == 'unresolved' for b in result))
            self.assertFalse(fidelity_report(result)['complete'])

    def test_matematica1_q56_url_underline_still_coalesces(self):
        # Actual archived crop geometry; image bytes are not needed for this rule.
        blocks, assets = crops({
            1: [345.24, 327.36, 560.88, 347.28],
            2: [350.88, 338.4, 555.84, 340.8],
            3: [104.65, 116.14, 554.09, 319.79],
        })
        original = copy.deepcopy((blocks, assets))
        result = importer.coalesce_visual_crops(blocks, assets, 'evidence')
        self.assertEqual([b['asset_id'] for b in result], ['crop-1', 'crop-3'])
        self.assertEqual(result[0]['source_ids'], blocks[0]['source_ids'] + blocks[1]['source_ids'])
        self.assertEqual((blocks, assets), original)

    def test_filadd_q28_q38_four_options_keep_exclusive_visual_owners(self):
        # LL geometry from the current archived source objects, rounded to 0.01pt.
        samples = [
            ([667.17, 515.67, 361.92, 207.42],
             [[75, 612.42, 210, 751.92], [75, 460.92, 211.5, 600.42],
              [75.75, 305.67, 221.25, 448.92], [75.75, 151.17, 225.75, 293.67]]),
            ([657.42, 500.67, 343.17, 184.17],
             [[75, 601.92, 231, 742.17], [75, 442.17, 224.25, 589.92],
              [75.75, 286.17, 231, 430.17], [75.75, 124.17, 222, 274.17]]),
        ]
        def token(text, box, sid):
            x, y, right, top = box
            return SimpleNamespace(text=text, x=x, y=y, width=right-x,
                                   height=top-y, font_size=12, source_id=sid)
        for ys, boxes in samples:
            labels = [token(f'{c})', [60, y, 72, y+12], f'p:label:{c}') for c, y in zip('ABCD', ys)]
            markers = [token(f'[Image: X{i}]', box, f'p:text:{i}') for i, box in enumerate(boxes)]
            objects = [{'type': 'PdfImage', 'bbox_ll': box, 'source_id': f'p:object:{i}'}
                       for i, box in enumerate(boxes)]
            members, object_members, ambiguous = importer.assign_exclusive_option_members(labels+markers, objects, labels)
            self.assertEqual(ambiguous, [])
            for i, c in enumerate('ABCD'):
                self.assertIn(markers[i], members[c])
                self.assertIn(objects[i], object_members[c])
                self.assertEqual(sum(markers[i] in v for v in members.values()), 1)
                block = importer.block_for_line({'text': markers[i].text, 'items': [markers[i]]},
                    'evidence', {f'X{i}': f'asset-{i}'}, f'option:{c}',
                    {f'asset-{i}': [objects[i]['source_id']]})
                self.assertEqual(block['type'], 'image')
                self.assertEqual(set(block['source_ids']), {markers[i].source_id, objects[i]['source_id']})
                self.assertEqual(importer.coalesce_visual_crops([block], {}, 'evidence'), [block])

    def candidate_draft(self, root):
        draft = fixture(root)
        q = draft['questions'][0]
        q['stem'] = [{'type': 'unresolved', 'reason': 'visual_overlap_unproven',
                      'candidate_type': 'visual', 'evidence_id': 'ev-a',
                      'source_ids': ['atom-math'], 'owner': 'stem', 'asset_id': 'graph-a'}]
        q['extraction_status'] = 'partial'
        q['structural_fidelity'] = {'complete': False, 'failures': []}
        draft['extraction']['status'] = 'partial'
        return draft

    def test_existing_v1_schema_accepts_linked_unresolved_without_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            draft = self.candidate_draft(root)
            validate_v1(draft, artifact_root=root, check_files=True)
            self.assertEqual(draft['questions'][0]['extraction_status'], 'partial')
            draft['questions'][0]['extraction_status'] = 'complete'
            draft['questions'][0]['structural_fidelity']['complete'] = True
            with self.assertRaises(DraftContractError):
                validate_v1(draft)

    def test_unresolved_candidate_cannot_reference_missing_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            draft = self.candidate_draft(Path(tmp))
            draft['questions'][0]['stem'][0]['asset_id'] = 'missing-asset'
            with self.assertRaisesRegex(DraftContractError, 'Unknown asset'):
                validate_v1(draft)

    def test_context_and_fragment_candidates_validate_asset_references(self):
        for container in ['contexts', 'unassigned_fragments']:
            with self.subTest(container=container), tempfile.TemporaryDirectory() as tmp:
                draft = self.candidate_draft(Path(tmp))
                block = copy.deepcopy(draft['questions'][0]['stem'][0])
                block['asset_id'] = 'missing-asset'
                entry = {'id': 'candidate-container', 'region_ids': ['region-a'],
                         'blocks': [block]}
                if container == 'unassigned_fragments':
                    entry['reason'] = 'ambiguous_visual'
                draft[container].append(entry)
                with self.assertRaisesRegex(DraftContractError, 'Unknown asset'):
                    validate_v1(draft)

    def test_candidate_asset_bytes_remain_subject_to_hash_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            draft = self.candidate_draft(root)
            (root / 'assets/graph.png').write_bytes(b'changed asset')
            with self.assertRaisesRegex(DraftContractError, 'Missing or changed artifact'):
                validate_v1(draft, artifact_root=root, check_files=True)


if __name__ == '__main__':
    unittest.main()
