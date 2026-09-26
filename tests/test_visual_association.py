"""Geometry/provenance regression fixtures; no real PDFs are opened."""
import sys
import unittest
import json
import tempfile
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/paes-importer/scripts'))
import import_benchmark as importer


def item(text, x, y, w=12, h=12, source_id=None):
    return SimpleNamespace(text=text, x=x, y=y, width=w, height=h,
                           font_size=12, source_id=source_id)


def raster(x, y, w, h, source_id=None):
    return {'type': 'PdfImage', 'bbox_ll': [x, y, x+w, y+h], 'source_id': source_id}


class VisualAssociationTests(unittest.TestCase):
    def setUp(self):
        importer._SOURCE_IDS.clear()

    def test_opaque_marker_names_emit_image_with_both_sources(self):
        for name in ['Im99', 'X62', 'Figure-7', 'Imagen_azul']:
            with self.subTest(name=name):
                marker = item(f'[Image: {name}]', 75, 600, 135, 140, 's-p1:text:0')
                obj = raster(75, 600, 135, 140, 's-p1:object:0')
                self.assertEqual(importer.associate_visual_objects([marker], [obj]), {name: [0]})
                block = importer.block_for_line({'text': marker.text, 'items': [marker]},
                    'ev', {name: 'asset'}, 'option:A', {'asset': ['s-p1:object:0']})
                self.assertEqual(block['type'], 'image')
                self.assertEqual(set(block['source_ids']), {'s-p1:text:0', 's-p1:object:0'})

    def test_same_geometry_different_page_is_not_associated(self):
        marker = item('[Image: X]', 75, 600, 135, 140, 's-p1:text:0')
        self.assertEqual(importer.associate_visual_objects([marker],
            [raster(75, 600, 135, 140, 's-p2:object:0')]), {})

    def test_two_markers_competing_for_one_object_remain_unresolved(self):
        markers = [item(f'[Image: {name}]', 75, 600, 135, 140) for name in ['X', 'Y']]
        for values in [markers, list(reversed(markers))]:
            self.assertEqual(importer.associate_visual_objects(values, [raster(75, 600, 135, 140)]), {})

    def test_duplicate_names_do_not_overwrite_association(self):
        markers = [item('[Image: X]', 75, y, 135, 140) for y in [600, 400]]
        self.assertEqual(importer.associate_visual_objects(markers,
            [raster(75, y, 135, 140) for y in [600, 400]]), {})

    def test_duplicate_objects_and_equal_distance_are_ambiguous(self):
        marker = item('[Image: X]', 75, 600, 135, 140)
        for objects in [[raster(75, 600, 135, 140)] * 2,
                        [raster(65, 600, 135, 140), raster(85, 600, 135, 140)]]:
            self.assertEqual(importer.associate_visual_objects([marker], objects), {})

    def test_vertical_graphs_and_two_column_grid_have_exclusive_owners(self):
        for coordinates in [[(60, 660), (60, 500), (60, 340), (60, 180)],
                            [(60, 660), (320, 660), (60, 400), (320, 400)]]:
            labels = [item(f'{label})', x, y) for label, (x, y) in zip('ABCD', coordinates)]
            visuals = [item(f'[Image: X{i}]', x+15, y-55, 135, 140) for i, (x,y) in enumerate(coordinates)]
            objects = [raster(x+15, y-55, 135, 140) for x,y in coordinates]
            members, object_members, ambiguous = importer.assign_exclusive_option_members(
                labels+visuals, objects, labels)
            self.assertEqual(ambiguous, [])
            for label, visual, obj in zip('ABCD', visuals, objects):
                self.assertIn(visual, members[label])
                self.assertIn(obj, object_members[label])
                self.assertEqual(sum(visual in values for values in members.values()), 1)

    def test_stem_graph_above_alternatives_stays_in_stem(self):
        labels = [item(f'{label})', 60, y) for label, y in zip('ABCD', [400, 300, 200, 100])]
        visual = item('[Image: X]', 75, 470, 135, 140)
        obj = raster(75, 470, 135, 140)
        members, object_members, ambiguous = importer.assign_exclusive_option_members(labels+[visual], [obj], labels)
        self.assertFalse(any(visual in v for v in members.values()))
        self.assertFalse(any(obj in v for v in object_members.values()))
        self.assertEqual(ambiguous, [])

    def test_graph_spanning_two_labels_is_not_assigned_to_top_label(self):
        labels = [item(f'{label})', 60, y) for label, y in zip('ABCD', [600, 520, 300, 100])]
        visual = item('[Image: X]', 75, 500, 135, 170)
        obj = raster(75, 500, 135, 170)
        members, object_members, ambiguous = importer.assign_exclusive_option_members(labels+[visual], [obj], labels)
        self.assertEqual(ambiguous, [visual, obj])

    def test_stem_graph_barely_overlapping_top_label_remains_ambiguous(self):
        labels = [item(f'{label})', 60, y) for label, y in zip('ABCD', [600, 400, 200, 100])]
        visual = item('[Image: X]', 75, 600, 135, 140)
        obj = raster(75, 600, 135, 140)
        _, _, ambiguous = importer.assign_exclusive_option_members(labels+[visual], [obj], labels)
        self.assertEqual(ambiguous, [visual, obj])

    def test_wide_graph_crossing_another_column_label_is_ambiguous(self):
        labels = [item('A)', 60, 600), item('B)', 200, 600)]
        self.assertIsNone(importer.aligned_visual_option([75, 550, 300, 690], labels))

    def test_raster_ambiguity_cannot_fall_back_to_vectors(self):
        marker = item('[Image: X]', 75, 600, 135, 140)
        objects = [raster(65, 600, 135, 140, 's:object:1'),
                   raster(85, 600, 135, 140, 's:object:2'),
                   {'type': 'PdfObject', 'bbox_ll': [75, 600, 200, 700], 'source_id': 's:object:3'}]
        def fake_asset(page, directory, asset_id, bbox, *args, **kwargs):
            return {'asset_id': asset_id}, {}
        with tempfile.TemporaryDirectory() as tmp, patch.object(importer, 'add_asset', side_effect=fake_asset):
            assets, mapping = importer.build_visual_assets(None, Path(tmp), 'q', [marker], objects, 600, 800, 'r')
        self.assertEqual(len(assets), 2)
        self.assertEqual(mapping, {})

    def _generate_visual_fixture(self, contained=False):
        from test_draft_v1_emitter import _SyntheticPdf, _SyntheticLayoutObject
        from draft_v1_emitter import staging_directory, publish_verified
        class PdfImage(_SyntheticLayoutObject):
            pass
        pdf = _SyntheticPdf()
        pdf.page.objects = []
        items = [item('1.', 30, 770), item('Seleccione el grafico.', 60, 770, 180)]
        for i, label in enumerate('ABCD'):
            y = 660 - i * 160
            items.extend([item(f'{label})', 60, y), item(f'[Image: X{i}]', 75, y-55, 135, 140)])
            pdf.page.objects.append(PdfImage((75, y-55, 210, y+85)))
        if contained:
            items.append(item('[Image: underline]', 80, 650, 120, 3))
            pdf.page.objects.append(PdfImage((80, 650, 200, 653)))
        for value in items:
            value.page = 1
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'synthetic.pdf'
            source.write_bytes(b'controlled mock source; not a real PDF')
            cases = root / 'cases.json'
            cases.write_text(json.dumps({'cases': [{'id': 'visual-q1', 'year': 2030, 'question': '1', 'page': 1}]}))
            target = root / 'published'
            with staging_directory(target) as stage:
                with patch.object(importer.pdfium, 'PdfDocument', return_value=pdf), patch.object(importer, 'extract_text_with_positions', return_value=items):
                    importer.generate_draft(cases, stage, {'2030': source})
                publish_verified(stage, target)
            draft = json.loads((target / 'draft.json').read_text(encoding='utf-8'))
            self.assertEqual(draft['schema_version'], '1.0.0')
            self.assertEqual(len(draft['assets']), 5 if contained else 4)
            question = draft['questions'][0]
            for option in question['options']:
                images = [block for block in option['blocks'] if block['type'] == 'image']
                self.assertEqual(len(images), 1)
                self.assertEqual(len(images[0]['source_ids']), 4 if contained and option['label'] == 'A' else 2)
            self.assertFalse(any(issue['code'] == 'AMBIGUOUS_ASSOCIATION' for issue in draft['issues']))

    def test_generate_v1_publishes_four_visual_options_with_provenance(self):
        self._generate_visual_fixture()

    def test_generate_v1_contained_crop_keeps_assets_and_all_provenance(self):
        self._generate_visual_fixture(contained=True)

    def crop_fixture(self, boxes, source_type='rendered_slice'):
        blocks = [{'type': 'image', 'asset_id': str(i), 'owner': 'stem',
                   'source_ids': [f'p:text:{i}', f'p:object:{i}']} for i in range(len(boxes))]
        assets = {str(i): {'source_bbox': box, 'source_type': source_type,
                          'region_ids': ['region']} for i, box in enumerate(boxes)}
        return blocks, assets

    def test_contained_page_crops_coalesce_all_sources_without_mutating_assets(self):
        import copy
        blocks, assets = self.crop_fixture([[0, 0, 200, 40], [5, 15, 195, 18]])
        original = copy.deepcopy((blocks, assets))
        result = importer.coalesce_visual_crops(blocks, assets, 'ev')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['asset_id'], '0')
        self.assertEqual(set(result[0]['source_ids']), set(sum([b['source_ids'] for b in blocks], [])))
        self.assertEqual((blocks, assets), original)

    def test_nested_and_equal_crops_keep_every_source_exactly_once(self):
        blocks, assets = self.crop_fixture([[10, 10, 15, 15], [0, 0, 100, 100],
                                           [5, 5, 50, 50], [0, 0, 100, 100]])
        result = importer.coalesce_visual_crops(blocks, assets, 'ev')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['asset_id'], '1')
        self.assertEqual(len(result[0]['source_ids']), 8)

    def test_partial_overlap_does_not_discard_legitimate_distinct_images(self):
        blocks, assets = self.crop_fixture([[0, 0, 100, 100], [50, 20, 150, 90]])
        result = importer.coalesce_visual_crops(blocks, assets, 'ev')
        self.assertEqual(len(result), 2)
        self.assertTrue(all(b['type'] == 'unresolved' and b['reason'] == 'visual_overlap_unproven' for b in result))
        self.assertEqual([b['source_ids'] for b in result], [b['source_ids'] for b in blocks])

    def test_containment_of_independent_image_streams_is_not_proof(self):
        blocks, assets = self.crop_fixture([[0, 0, 100, 100], [10, 10, 20, 20]], 'embedded_image')
        result = importer.coalesce_visual_crops(blocks, assets, 'ev')
        self.assertTrue(all(b['type'] == 'unresolved' for b in result))

    def test_containment_requires_matching_region_provenance(self):
        blocks, assets = self.crop_fixture([[0, 0, 100, 100], [10, 10, 20, 20]])
        assets['1']['region_ids'] = ['other-region']
        self.assertTrue(all(b['type'] == 'unresolved' for b in importer.coalesce_visual_crops(blocks, assets, 'ev')))

    def test_independent_and_touching_visuals_remain_independent(self):
        blocks, assets = self.crop_fixture([[0, 0, 100, 100], [100, 0, 200, 100], [0, 110, 100, 200]])
        self.assertEqual(importer.coalesce_visual_crops(blocks, assets, 'ev'), blocks)

    def test_partial_overlap_taints_containment_family_conservatively(self):
        blocks, assets = self.crop_fixture([[0, 0, 100, 100], [10, 10, 20, 20], [90, 0, 120, 100]])
        result = importer.coalesce_visual_crops(blocks, assets, 'ev')
        self.assertEqual(len(result), 3)
        self.assertTrue(all(b['type'] == 'unresolved' for b in result))


if __name__ == '__main__':
    unittest.main()
