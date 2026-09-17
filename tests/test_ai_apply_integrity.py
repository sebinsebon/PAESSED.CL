"""Generic regressions for the real host-CLI apply boundary."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/paes-importer/scripts'))
from ai_on_demand import apply_ai_response, build_ai_request, validate_ai_response
from structural_fidelity import fidelity_report


class ApplyIntegrityTests(unittest.TestCase):
    def fixture(self, owner='stem', proof=True):
        candidate = {'type': 'unresolved', 'candidate_id': 'candidate-x',
                     'candidate_type': 'math', 'reason': 'ambiguous',
                     'owner': owner, 'source_ids': ['source-x']}
        if proof:
            candidate['structural_fidelity'] = {
                'status': 'unresolved', 'bbox_ll': [0, 0, 10, 10], 'baseline': 0,
                'source_ids': ['source-x'], 'representation_type': 'unresolved'}
        question = {'id': 'q', 'region_ids': ['r'], 'stem': [],
                    'options': [{'id': 'A', 'blocks': []}]}
        (question['stem'] if owner == 'stem' else question['options'][0]['blocks']).append(candidate)
        draft = {'questions': [question], 'source_objects': [
            {'id': 'source-x', 'region_id': 'r', 'owner': owner, 'kind': 'text'}],
            'issues': [], 'extraction': {'ai_interventions': []}}
        response = {'schema_version': '1.0', 'candidate_id': 'candidate-x',
                    'action': 'replace', 'agent': {'cli': 'test', 'model': 'test'},
                    'result': {'type': 'math', 'latex': '2+3', 'display': False,
                               'owner': owner, 'source_ids': ['source-x']}}
        return draft, response

    def test_option_replacement_is_in_place_without_appending_to_stem(self):
        draft, response = self.fixture('option:A')
        updated = apply_ai_response(draft, response)
        q = updated['questions'][0]
        self.assertEqual(q['stem'], [])
        self.assertEqual(q['options'][0]['blocks'][0]['type'], 'math')
        self.assertEqual(q['coverage']['duplicated'], [])
        self.assertEqual(q['extraction_status'], 'partial')

    def test_stem_apply_preserves_unrelated_options(self):
        draft, response = self.fixture()
        draft['questions'][0]['options'][0]['blocks'] = [{'type': 'text', 'text': 'choice'}]
        before = copy.deepcopy(draft['questions'][0]['options'])
        apply_ai_response(draft, response)
        self.assertEqual(len(draft['questions'][0]['stem']), 1)
        self.assertEqual(draft['questions'][0]['options'], before)

    def test_candidate_without_geometry_remains_partial_without_crashing(self):
        draft, response = self.fixture(proof=False)
        updated = apply_ai_response(draft, response)
        self.assertEqual(updated['questions'][0]['extraction_status'], 'partial')
        self.assertFalse(updated['questions'][0]['structural_fidelity']['complete'])

    def test_retain_preserves_other_pending_issues_and_records_reason(self):
        draft, response = self.fixture()
        draft['issues'] = [{'id': 'pending', 'target_id': 'q',
                            'code': 'PENDING_MATH_RECONSTRUCTION', 'blocks_completion': True}]
        response['action'] = 'retain_unresolved'
        response['result'] = {'type': 'unresolved', 'reason': 'crop truncated',
                              'owner': 'stem', 'source_ids': ['source-x']}
        updated = apply_ai_response(draft, response)
        self.assertTrue(any(i['code'] == 'PENDING_MATH_RECONSTRUCTION' for i in updated['issues']))
        self.assertEqual(updated['extraction']['ai_interventions'][0]['response'], response)

    def test_request_does_not_silently_fall_back_to_full_question(self):
        candidate = {'candidate_id': 'x', 'evidence_id': 'full'}
        with self.assertRaises(ValueError):
            build_ai_request(candidate, [{'id': 'full', 'path': 'full.png'}])

    def test_fidelity_issue_is_refreshed_after_apply(self):
        draft, response = self.fixture()
        draft['issues'] = [{'id': 'fidelity', 'target_id': 'q',
                            'code': 'STRUCTURAL_FIDELITY_UNPROVEN', 'failures': ['old']}]
        updated = apply_ai_response(draft, response)
        issue = next(i for i in updated['issues']
                     if i['code'] == 'STRUCTURAL_FIDELITY_UNPROVEN')
        self.assertEqual(issue['failures'],
                         updated['questions'][0]['structural_fidelity']['failures'])

    def test_malformed_table_response_is_rejected_at_schema_boundary(self):
        draft, response = self.fixture()
        response['result'] = {
            'type': 'table', 'rows': ['invalid-row'],
            'owner': 'stem', 'source_ids': ['source-x'],
        }
        with self.assertRaises(ValueError):
            apply_ai_response(draft, response)

    def test_table_block_empty_object_is_rejected(self):
        draft, response = self.fixture()
        response['result'] = {
            'type': 'table',
            'rows': [{'cells': [{'blocks': [{}]}]}],
            'owner': 'stem', 'source_ids': ['source-x'],
        }
        with self.assertRaises(ValueError):
            validate_ai_response(response, draft['questions'][0]['stem'][0])

    def test_valid_table_block_is_accepted(self):
        draft, response = self.fixture()
        response['result'] = {
            'type': 'table',
            'rows': [{'cells': [{'blocks': [{'type': 'text', 'text': 'visible'}]}]}],
            'owner': 'stem', 'source_ids': ['source-x'],
        }
        self.assertIs(validate_ai_response(response, draft['questions'][0]['stem'][0]), response)

    def test_retain_uses_distinct_issue_code_and_upserts_on_retry(self):
        draft, response = self.fixture()
        response['action'] = 'retain_unresolved'
        response['result'] = {
            'type': 'unresolved', 'reason': 'crop truncated',
            'owner': 'stem', 'source_ids': ['source-x'],
        }
        first = apply_ai_response(copy.deepcopy(draft), response)
        second = apply_ai_response(first, response)
        pending = [i for i in second['issues'] if i['id'] == 'issue-ai-candidate-x']
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]['code'], 'AI_RESPONSE_RETAINED_UNRESOLVED')
        self.assertEqual(second['questions'][0]['stem'][0]['ai_on_demand']['reason'], 'crop truncated')

    def test_none_baseline_is_reported_as_missing_geometry(self):
        block = {'type': 'math', 'latex': 'x', 'owner': 'stem',
                 'source_ids': ['source-x'],
                 'structural_fidelity': {
                     'status': 'verified', 'baseline': None,
                     'bbox_ll': [0, 0, 1, 1], 'source_ids': ['source-x'],
                     'representation_type': 'math',
                 }}
        report = fidelity_report([block])
        self.assertFalse(report['complete'])
        self.assertIn('missing_source_geometry', report['failures'][0]['reasons'])


if __name__ == '__main__':
    unittest.main()
