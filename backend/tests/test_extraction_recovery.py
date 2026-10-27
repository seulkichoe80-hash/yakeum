"""Candidate-local recovery without live API calls or contract changes."""
import pytest
from backend.tests.test_extraction_contract import CONTEXT, medication, response
from backend.services.extraction import adapt_gemini_response, ExtractionContext


@pytest.mark.parametrize('slots', ['GE', 'EG', 'GEG', 'EE'])
def test_bad_number_keeps_slots_and_source_order(slots):
    values = [medication(dose_per_administration='읽기불가') if s == 'E' else medication() for s in slots]
    results = adapt_gemini_response(response(*values), CONTEXT)
    assert len(results) == len(slots)
    for index, (slot, result) in enumerate(zip(slots, results), 1):
        assert set(result) == {'status', 'record', 'warnings', 'errors'}
        if slot == 'E':
            assert result['status'] == 'FAILED'
            assert result['record'] is None
            assert result['errors'][0]['code'] == 'AI_EXTRACTION_FAILED'
            assert f'후보 {index}' in result['errors'][0]['message']
            assert '읽기불가' not in str(result)
        else:
            assert result['status'] == 'SUCCESS'
            assert result['record']['source_record_id'] == f'{CONTEXT.source_document_id}:{index}'
            assert result['record']['user_confirmed'] is False


@pytest.mark.parametrize('ingredients', [[], [{}], [{'ingredient_name_raw': None, 'product_strength': None, 'product_strength_unit': None}], [{'ingredient_name_raw':'가상성분'}]])
def test_unverified_ingredients_preserve_candidate_and_warn(ingredients):
    result = adapt_gemini_response(response(medication(ingredients=ingredients)), CONTEXT)[0]
    assert result['status'] == 'NEEDS_CONFIRMATION'
    assert result['record'] is not None
    assert result['record']['user_confirmed'] is False
    assert len(result['record']['ingredients']) == len(ingredients)
    assert any(w['field'].startswith('ingredients') for w in result['warnings'])


def test_partial_combination_keeps_known_ingredient():
    known = medication()['ingredients'][0]
    result = adapt_gemini_response(response(medication(ingredients=[known, {}])), CONTEXT)[0]
    assert result['record']['ingredients'][0]['product_strength'] == '100'
    assert result['record']['ingredients'][1]['ingredient_name_raw'] is None
    assert any(w['field'] == 'ingredients[1]' for w in result['warnings'])


@pytest.mark.parametrize('raw', ['bad-json', '{"medications":{}}', '[1,2]', '{"medications":null}'])
def test_document_structure_still_fails_whole_document(raw):
    result = adapt_gemini_response(raw, CONTEXT)
    assert len(result) == 1 and result[0]['status'] == 'FAILED'


def test_family_mismatch_overrides_mixed_candidates():
    raw = response(medication(), medication(dose_per_administration='읽기불가'), family_member_id='00000000-0000-4000-8000-000000000002')
    results = adapt_gemini_response(raw, CONTEXT)
    assert len(results) == 1 and results[0]['status'] == 'FAILED'


def test_bad_caller_overrides_mixed_candidates():
    results = adapt_gemini_response(response(medication(), medication(dose_per_administration='읽기불가')), ExtractionContext('', 'virtual', '2026-10-27'))
    assert len(results) == 1 and results[0]['status'] == 'FAILED'


def test_confidence_is_not_accuracy_or_user_confirmation():
    result = adapt_gemini_response(response(medication(confidence='0.1')), CONTEXT)[0]
    assert result['status'] == 'SUCCESS'  # no invented threshold
    assert result['record']['confidence'] == '0.1'
    assert result['record']['user_confirmed'] is False
