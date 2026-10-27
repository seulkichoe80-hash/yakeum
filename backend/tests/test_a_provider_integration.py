"""D-only integration checks for published A, with real SDK/in-memory transport.

run_fake_extraction is also usable by the temporary local browser harness. It
never adds an endpoint or changes the production LOCAL_MOCK routing.
"""
from copy import deepcopy
import json
from unittest.mock import patch

from google import genai
import httpx

from backend.api import extraction_provider, photo_demo
from backend.services.extraction import ExtractionContext, GeminiSettings
from backend.services.extraction.sdk import count_analysis_requests
from backend.services.reconciliation.current_intake import apply_user_verification
from backend.tests.test_photo_demo import FAMILY, document, payload, process

_REAL_CLIENT = genai.Client


def run_fake_extraction(family, doc, *, raw=None, http_status=200, calls=None):
    """Published provider + real SDK; HTTPX MockTransport forbids live traffic."""
    calls = calls if calls is not None else []
    if raw is None:
        raw = photo_demo._fixture(doc.scenario)
        if doc.scenario != 'failed':
            data = json.loads(raw)
            data['document_type'] = {'MEDICINE_BAG': '약봉투', 'PRESCRIPTION': '처방전',
                                     'SUPPLEMENT': '건강기능식품'}[doc.source_type]
            raw = json.dumps(data, ensure_ascii=False)

    def handler(request):
        calls.append(request)
        if http_status != 200:
            return httpx.Response(http_status, json={'error': {
                'code': http_status, 'status': 'UNAVAILABLE', 'message': 'private-provider-marker'}})
        return httpx.Response(200, json={'candidates': [{'content': {
            'role': 'model', 'parts': [{'text': raw}]}, 'finishReason': 'STOP'}]})

    def client(*args, **kwargs):
        options = kwargs['http_options']
        assert options.retry_options.attempts == 1
        assert options.timeout == 60000
        options.client_args.update(transport=httpx.MockTransport(handler), trust_env=False)
        return _REAL_CLIENT(*args, **kwargs)

    context = ExtractionContext(family, str(doc.document_id), doc.record_date.isoformat())
    with patch.object(genai, 'Client', side_effect=client), patch.object(
            GeminiSettings, 'from_environment', return_value=GeminiSettings('fake-model', 'fake-key')):
        with count_analysis_requests() as counter:
            result = extraction_provider.extract_image_candidates(b'synthetic-image', 'image/png', context)
        assert counter[0] == 1
    return result


def test_published_provider_to_review_b_d_and_separate_intake():
    body = payload()
    body['current']['reviews'][0]['draft']['dose'] = '2'
    before = deepcopy(body)
    calls = []
    with patch.object(photo_demo, 'extract_virtual', side_effect=lambda family, doc:
                      run_fake_extraction(family, doc, calls=calls)):
        preview = process(body)
        assert preview['stage'] == 'normalized'
        assert preview['reconciliation_result'] is None
        compared = process({**body, 'normalization_confirmed': True})
    assert body == before
    assert len(calls) == 4  # two explicit docs, preview + final review
    assert compared['stage'] == 'compared'
    item = compared['reconciliation_result']['items'][0]
    assert item['status'] == 'DOSE_CHANGED'
    assert item['previous_record']['dose_per_administration'] == '1'
    assert item['current_record']['dose_per_administration'] == '2'
    assert compared['original_results']['current'][0]['record']['user_confirmed'] is False
    state = compared['current_intake_states'][0]
    assert (state['intake_status'], state['verification_status']) == ('UNKNOWN', 'PENDING')
    verified = apply_user_verification(state, 'TAKING', family_member_id=FAMILY,
        verified_by='virtual-user', last_verified_at='2026-10-26T00:00:00Z')
    assert verified['intake_status'] == 'TAKING'
    assert compared['current_intake_states'][0] == state
    assert state['intake_status'] == 'UNKNOWN'


def test_provider_failure_after_success_returns_no_previous_comparison():
    body = payload(confirmed=True)
    with patch.object(photo_demo, 'extract_virtual', side_effect=run_fake_extraction):
        assert process(body)['stage'] == 'compared'
    calls = []
    with patch.object(photo_demo, 'extract_virtual', side_effect=lambda family, doc:
                      run_fake_extraction(family, doc, http_status=503, calls=calls)):
        failed = process(body)
    assert len(calls) == 2  # one failed request per document; no retries
    assert failed['stage'] == 'held'
    assert failed['reconciliation_result'] is None
    assert failed['current_intake_states'] == []
    assert all(failed['original_results'][side][0]['status'] == 'FAILED' for side in ['previous', 'current'])
    assert 'private-provider-marker' not in json.dumps(failed)


def test_mixed_numeric_failure_preserves_valid_candidate():
    """The original defect is a regular regression after leader authorization."""
    value = json.loads(photo_demo._fixture('single'))
    value['medications'].append({**deepcopy(value['medications'][0]),
                                'dose_per_administration': '읽기불가'})
    doc = photo_demo.DocumentInput.model_validate(document('current'))
    result = run_fake_extraction(FAMILY, doc, raw=json.dumps(value, ensure_ascii=False))
    assert len(result) == 2
    assert result[0]['status'] == 'SUCCESS'
    assert result[1]['status'] == 'FAILED'
    assert result[1]['record'] is None
    assert result[1]['errors'][0]['code'] == 'AI_EXTRACTION_FAILED'


def test_fake_sdk_context_and_source_ids_remain_caller_owned():
    doc = photo_demo.DocumentInput.model_validate(document('current', 'multiple'))
    result = run_fake_extraction(FAMILY, doc)
    assert len(result) == 2
    assert [r['record']['source_record_id'] for r in result] == [
        f'{doc.document_id}:1', f'{doc.document_id}:2']
    assert all(r['record']['family_member_id'] == FAMILY for r in result)
    assert all(r['record']['user_confirmed'] is False for r in result)
    assert all(r['record']['mfds_product_id'] is None for r in result)


def test_a_requested_mixed_candidate_recovery():
    """Desired behavior stays visible as a strict expected failure, not a weakened test."""
    value = json.loads(photo_demo._fixture('single'))
    value['medications'].append({**deepcopy(value['medications'][0]),
                                'dose_per_administration': '읽기불가'})
    doc = photo_demo.DocumentInput.model_validate(document('current'))
    result = run_fake_extraction(FAMILY, doc, raw=json.dumps(value, ensure_ascii=False))
    assert len(result) == 2
    assert result[0]['status'] == 'SUCCESS'
    assert result[0]['record']['source_record_id'] == f'{doc.document_id}:1'
    assert result[1]['status'] == 'FAILED'
    assert result[1]['record'] is None


def test_recovered_mixed_candidates_reach_d_hold_without_deleting_good_record():
    value = json.loads(photo_demo._fixture('single'))
    value['medications'].append({**deepcopy(value['medications'][0]),
                                'dose_per_administration': '읽기불가'})
    raw = json.dumps(value, ensure_ascii=False)
    with patch.object(photo_demo, 'extract_virtual', side_effect=lambda family, doc:
                      run_fake_extraction(family, doc, raw=raw)):
        result = process(payload(confirmed=True))
    assert result['stage'] == 'held'
    assert result['reconciliation_result'] is None
    assert result['current_intake_states'] == []
    for side in ('previous', 'current'):
        originals = result['original_results'][side]
        assert len(originals) == 2
        assert originals[0]['record']['product_name_raw'] == '가상알파정'
        assert originals[1]['status'] == 'FAILED'
