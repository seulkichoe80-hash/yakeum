"""TASK D v2 policy integration; all workbooks and medicines are synthetic."""
from copy import deepcopy
from io import BytesIO
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.api.main import app
from backend.api.hira_hold import process_guarded
from backend.tests.test_b_d_c_api import _xlsx, _row, FAMILY_ID

pytestmark = pytest.mark.anyio

@pytest.fixture
def anyio_backend():
    return 'asyncio'


def known(number=1, date='2026-09-01', code='000123456'):
    row = _row(number, date, '가상제품', code)
    row[6] = None  # B may fill from its LOCAL_MOCK official entry; never infer a strength.
    return row


async def post(previous, current, version=2):
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        return await client.post(f'/api/v{version}/reconciliations/hira',
            data={'family_member_id': FAMILY_ID},
            files={side+'_file': (side+'.xlsx', _xlsx(rows)) for side, rows in [('previous',previous),('current',current)]})


def assert_sources(body):
    for row in body['source_rows']:
        _, bucket, side, index = row['normalization_ref'].split('/')
        result = body[bucket][side][int(index)]
        assert result['status'] in {'MATCHED','PARTIAL','UNMATCHED','FAILED'}
        assert set(row['raw_fields']) <= {'product_name','drug_code','date','dispensing_date','ingredient','strength','unit','dose_per_time','times_per_day','total_days'}
        assert 'file' not in row['raw_fields']
    assert len(body['source_rows']) == sum(len(body[b][s]) for b in ['accepted_results','review_results'] for s in ['previous','current'])


async def test_known_hira_executes_and_preserves_core_meanings():
    body=(await post([known()],[known(date='2026-10-01')])).json()
    assert body['response_version']=='TASK_D_HIRA_V2'
    assert body['comparison']=={'executed':True,'holds':[]}
    assert body['reconciliation_result']['items'][0]['status']=='MAINTAINED'
    assert body['reconciliation_result']['items'][0]['reason_code']=='SAME_INGREDIENT_SAME_STRENGTH'
    assert body['current_intake_states'][0]['intake_status']=='UNKNOWN'
    assert_sources(body)


@pytest.mark.parametrize('problem,kind',[
    ('failure','UNIDENTIFIED_FAILED_INPUT'),('strength','UNKNOWN_COMPARISON_FIELDS'),
    ('ingredient','UNKNOWN_COMPARISON_FIELDS'),('repeat','AMBIGUOUS_REPEATED_RECORDS'),
    ('dose','UNKNOWN_COMPARISON_FIELDS')])
async def test_entire_comparison_held_and_no_engine_called(problem,kind):
    current=[known()]
    if problem=='failure': current.append(_row(9,'invalid',None,None))
    if problem=='strength': current=[_row(1,'2026-10-01','가상미등록약','000000001')]
    if problem=='ingredient': current=[_row(1,'2026-10-01','가상미등록약',None)];current[0][6]=None
    if problem=='repeat': current.append(known(2))
    if problem=='dose': current[0][9]=None
    with patch('backend.api.hira_hold.reconcile_normalization_results',side_effect=AssertionError('held engine must not execute')):
        response=await post([known()],current)
    assert response.status_code==200
    body=response.json()
    assert body['comparison']['executed'] is False
    assert kind in {h['kind'] for h in body['comparison']['holds']}
    assert body['reconciliation_result'] is None
    assert body['current_intake_states']==[]
    assert_sources(body)
    assert all(len(h['affected_refs'])==len(body['source_rows']) for h in body['comparison']['holds'])
    if problem=='failure':
        assert body['review_results']['current'][0]['record'] is None
        assert any(r['raw_fields'].get('dispensing_date')=='invalid' for r in body['source_rows'])


@pytest.mark.parametrize('reverse_side',[False,True])
@pytest.mark.parametrize('reverse_order',[False,True])
async def test_repeat_direction_order_always_held_without_losing_rows(reverse_side,reverse_order):
    rows=[known(1),known(2,date='2026-08-01')]
    if reverse_order: rows.reverse()
    previous,current=([known()],rows) if reverse_side else (rows,[known()])
    body=(await post(previous,current)).json()
    assert [h['kind'] for h in body['comparison']['holds']]==['AMBIGUOUS_REPEATED_RECORDS']
    assert len(body['source_rows'])==3
    assert sum(len(v) for v in body['accepted_results'].values())==3
    assert body['reconciliation_result'] is None


async def test_held_then_normal_reprocess_and_legacy_unchanged():
    bad=[_row(1,'2026-10-01','가상미등록약','000000001')]
    assert (await post([known()],bad)).json()['reconciliation_result'] is None
    assert (await post([known()],[known()])).json()['comparison']['executed'] is True
    legacy=(await post(bad,bad,1)).json()
    assert 'comparison' not in legacy and 'response_version' not in legacy
    assert legacy['reconciliation_result']['items'][0]['status']=='MAINTAINED'


async def test_normal_zero_result_is_not_hold():
    body=(await post([],[])).json()
    assert body['comparison']=={'executed':True,'holds':[]}
    assert body['reconciliation_result']['items']==[]
    assert body['source_rows']==[]


async def test_both_failed_hold_preserves_null_candidates():
    body=(await post([_row(1,'invalid',None,None)],[_row(2,'invalid',None,None)])).json()
    assert body['reconciliation_result'] is None
    assert len(body['review_results']['previous'])==1
    assert len(body['review_results']['current'])==1
    assert_sources(body)


def test_gate_does_not_mutate_normalization_or_expose_unneeded_raw_fields():
    from backend.services.normalization.models import MedicationRecord, NormalizationResult
    raw=NormalizationResult('FAILED',MedicationRecord(raw_row={
        'product_name':'가상약','strength':'미확인 원문','patient_name':'do not return',
        'prescribing_institution':'do not return'},source_ref={'file':'/private/path','sheet':'private title','row':3}))
    failed={'status':'FAILED','record':None,'warnings':[],'errors':[],'match':{'source':None,'official_id':None,'match_method':None}}
    before=deepcopy(failed)
    body=process_guarded([failed],[],[raw],[],FAMILY_ID)
    assert failed==before
    assert body['review_results']['previous'][0]==before
    assert body['source_rows'][0]['raw_fields']=={'product_name':'가상약','strength':'미확인 원문'}
    assert body['source_rows'][0]['locator']=={'sheet_index':None,'row':3}
    assert raw.record.source_ref['file']=='/private/path'


async def test_missing_dose_is_unknown_but_zero_is_known():
    row=known();row[9]='0'
    body=(await post([row],[row])).json()
    assert body['comparison']['executed'] is True
    assert body['accepted_results']['current'][0]['record']['dose_per_administration']=='0'


async def test_optional_hira_metadata_and_duration_do_not_hold_normal_comparison():
    """Optional XLSX cells stay unknown without disabling a fully comparable pair."""
    previous, current = known(), known(date='2026-10-01')
    for row in (previous, current):
        for index in (0, 2, 3, 5, 11):
            row[index] = None  # row number, institutions, category and duration
    body = (await post([previous], [current])).json()
    assert body['comparison'] == {'executed': True, 'holds': []}
    item = body['reconciliation_result']['items'][0]
    assert item['status'] == 'MAINTAINED'
    assert item['reason_code'] == 'SAME_INGREDIENT_SAME_STRENGTH'
    for result in body['accepted_results']['previous'] + body['accepted_results']['current']:
        record = result['record']
        assert record['duration_days'] is None
        assert record['prescribing_institution'] is None
        assert record['dispensing_institution'] is None
        assert record['drug_category'] is None
        assert record['confidence'] is None
        assert record['user_confirmed'] is False
        assert all(i['official_ingredient_id'] is None for i in record['ingredients'])
    assert_sources(body)
