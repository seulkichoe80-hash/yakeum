"""Existing-config safety tests, NOT official-spec conformance or live evidence."""
from copy import deepcopy
from unittest.mock import patch

import pytest
import yaml

from backend.api import photo_demo
from backend.services.mfds.real_client import DEFAULT_CONFIG, RealMfdsClient
from backend.services.normalization.adapter import validate_common_result
from backend.services.normalization.structured import normalize_structured_record
from backend.tests.test_photo_demo import FAMILY, payload


@pytest.fixture
def drug_client(tmp_path):
    # The existing field assumptions remain unverified; no production config edit.
    config = yaml.safe_load(DEFAULT_CONFIG.read_text())
    config['sources'].pop('health_food')
    path = tmp_path / 'synthetic-drug-only.yaml'
    path.write_text(yaml.safe_dump(config))

    def build(rows=None, error=False):
        calls = []

        def transport(url, params, timeout):
            calls.append(True)  # Never retain keyed URLs or request contents.
            if error:
                raise TimeoutError('SYNTHETIC ONLY')
            return {'header': {'resultCode': '00'},
                    'body': {'items': rows or [], 'totalCount': len(rows or [])}}

        return RealMfdsClient(api_key='SYNTHETIC-NOT-A-KEY', retries=0,
                              transport=transport, config_path=path), calls
    return build


def item(identifier='SYNTHETIC-001', name='가상알파정'):
    return {'ITEM_SEQ': identifier, 'ITEM_NAME': name,
            'MAIN_ITEM_INGR': '가상알파성분'}


@pytest.mark.parametrize('case,expected', [
    ('empty', 'UNMATCHED'), ('multiple', 'PARTIAL'),
    ('unknown_strength', 'MATCHED'), ('error', 'UNMATCHED')])
def test_photo_offline_single_source_holds_and_preserves_candidates(drug_client, case, expected):
    rows = [] if case == 'empty' else [item()]
    if case == 'multiple':
        rows.append(item('SYNTHETIC-002'))
    mfds, calls = drug_client(rows, error=case == 'error')
    request = payload(confirmed=True)
    if case == 'unknown_strength':
        for side in ('previous', 'current'):
            request[side]['reviews'][0]['draft']['ingredients'][0]['strength'] = ''
            request[side]['reviews'][0]['draft']['ingredients'][0]['unit'] = ''
    before = deepcopy(request)
    # Use the actual photo coordinator and B/D guard, but never a live transport.
    with patch.object(photo_demo, '_catalog', return_value=mfds), patch(
        'backend.services.mfds.real_client.default_transport',
        side_effect=AssertionError('external API forbidden')):
        result = photo_demo.process_virtual(photo_demo.ProcessInput(**request))
    assert calls and len(calls) <= 2  # Two sides; cache can avoid the second call.
    assert request == before
    assert result['stage'] == 'held' and result['pending_decisions']
    assert result['reconciliation_result'] is None  # Not a successful empty comparison.
    assert result['current_intake_states'] == []
    for side in ('previous', 'current'):
        assert len(result['original_results'][side]) == 1
        assert result['original_results'][side][0]['record']['user_confirmed'] is False
        normalized = result['normalization_results'][side][0]
        assert normalized['status'] == expected
        assert normalized['record'] is not None
        assert normalized['record']['user_confirmed'] is False
        assert validate_common_result(normalized) == []
        if case == 'unknown_strength':
            assert normalized['record']['ingredients'][0]['product_strength'] is None
    assert mfds.last_failed is (case == 'error')


def test_name_candidate_does_not_verify_or_replace_source_strength(drug_client):
    # normalize_name removes 200mg/100mg; NAME_EXACT is not strength equality.
    mfds, calls = drug_client([item(name='가상알파정200mg')])
    source = photo_demo.extract_virtual(FAMILY, photo_demo.DocumentInput(
        **{k: v for k, v in payload()['current'].items() if k != 'reviews'}))[0]
    before = deepcopy(source)
    result = normalize_structured_record(source, mfds, expected_family_member_id=FAMILY)
    assert result['status'] == 'MATCHED'  # Existing product-candidate contract retained.
    assert result['match']['match_method'] == 'NAME_EXACT'
    assert any('공식 일치 검증은 수행하지 않았습니다' in w['message'] for w in result['warnings'])
    for field in ('ingredient_name_raw', 'product_strength', 'product_strength_unit', 'official_ingredient_id'):
        assert result['record']['ingredients'][0][field] == before['record']['ingredients'][0][field]
    assert result['record']['ingredients'][0]['product_strength'] == '100'
    assert result['record']['ingredients'][0]['official_ingredient_id'] is None
    assert result['record']['user_confirmed'] is False and source == before
    assert validate_common_result(result) == [] and len(calls) == 1
    assert mfds.find_by_code('000123456') == [] and len(calls) == 1
