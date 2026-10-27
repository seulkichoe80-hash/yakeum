"""Owned HIRA persistence with synthetic accounts/workbooks; no live services."""
from copy import deepcopy
import json
from unittest.mock import patch
from uuid import uuid4
import pytest
from backend.tests.test_dev_account import environment, account, family, processed, save as save_photo, PASSWORD, ORIGIN
from backend.tests.test_b_d_c_api import _xlsx, _row
from backend.tests.test_hira_hold_v2 import known
from backend.storage.local_db import database
from fastapi.testclient import TestClient
from backend.api.main import app


def process(c,f,previous=None,current=None):
    return c.post(f'/api/dev-account/families/{f}/hira/process',files={
        'previous_file':('virtual-previous.xlsx',_xlsx([known()] if previous is None else previous)),
        'current_file':('virtual-current.xlsx',_xlsx([known(date='2026-10-01')] if current is None else current))})


def saved(c,f,run,choices=None):
    response=c.post(f'/api/dev-account/families/{f}/hira-runs/{run}/save',json={'intake_confirmations':choices or []})
    assert response.status_code==200,response.text
    response=c.get(f'/api/dev-account/families/{f}/hira-runs/{run}')
    assert response.status_code==200,response.text
    return response.json()


def test_hira_save_relogin_original_normalized_comparison_and_pending_preserved():
    c=account();f=family(c)
    response=process(c,f);assert response.status_code==200,response.text
    original=response.json();value=saved(c,f,original['run_id'])
    assert value['result']==original['result']
    assert value['result']['comparison']=={'executed':True,'holds':[]}
    assert value['result']['source_rows']
    assert value['result']['accepted_results']['current'][0]['record']['drug_code']=='000123456'
    assert value['result']['accepted_results']['current'][0]['record']['user_confirmed'] is False
    assert value['intake_states'][0]['verification_status']=='PENDING'
    assert value['intake_states'][0]['intake_status']=='UNKNOWN'
    assert c.post('/api/dev-account/logout').status_code==200
    assert c.get(f'/api/dev-account/families/{f}/hira-runs/{original["run_id"]}').status_code==401
    login=c.post('/api/dev-account/login',json={'username':'synthetic_a','password':PASSWORD})
    c.headers['X-CSRF-Token']=login.json()['csrf_token']
    assert c.get(f'/api/dev-account/families/{f}/hira-runs/{original["run_id"]}').json()==value


@pytest.mark.parametrize('problem',['failure','strength','repeat','empty'])
def test_hold_and_executed_zero_remain_distinct_after_storage(problem):
    c=account();f=family(c)
    rows=[known()]
    if problem=='failure':rows.append(_row(9,'invalid',None,None))
    if problem=='strength':rows=[_row(1,'2026-10-01','가상미등록약','000000001')]
    if problem=='repeat':rows.append(known(2))
    response=process(c,f,previous=[] if problem=='empty' else None,current=[] if problem=='empty' else rows)
    assert response.status_code==200
    original=response.json();value=saved(c,f,original['run_id'])
    assert value['result']==original['result']
    result=value['result']
    if problem=='empty':
        assert result['comparison']['executed'] is True
        assert result['reconciliation_result']['items']==[]
    else:
        assert result['comparison']['executed'] is False
        assert result['comparison']['holds'] and result['source_rows']
        assert result['reconciliation_result'] is None
    assert value['intake_states']==[]
    path=f'/api/dev-account/families/{f}/hira-runs/{original["run_id"]}/intake'
    assert c.patch(path,json={'record_id':str(uuid4()),'choice':'TAKING'}).status_code==422


def test_explicit_intake_only_changes_separate_state_and_never_confirms_source():
    c=account();f=family(c);run=process(c,f).json()['run_id'];value=saved(c,f,run)
    result=deepcopy(value['result']);record=value['intake_states'][0]['medication_record_id']
    path=f'/api/dev-account/families/{f}/hira-runs/{run}'
    for choice in ['TAKING','NOT_TAKING','UNKNOWN']:
        assert c.patch(path+'/intake',json={'record_id':record,'choice':choice}).status_code==200
        value=c.get(path).json()
        assert value['intake_states'][0]['intake_status']==choice
        assert value['intake_states'][0]['verification_status']=='USER_VERIFIED'
        assert value['intake_states'][0]['verified_by'] and value['intake_states'][0]['last_verified_at']
        assert value['result']==result
    assert saved(c,f,run)['intake_states'][0]['verification_status']=='USER_VERIFIED'
    assert len(c.get(f'/api/dev-account/families/{f}/hira-runs').json()['runs'])==1


def test_two_users_several_families_cannot_read_or_modify_each_others_runs():
    a=account();b=account('synthetic_b');fa=family(a);fa2=family(a,'가상 가족2');fb=family(b)
    run=process(a,fa).json()['run_id'];saved(a,fa,run)
    for c,f in [(b,fa),(b,fb),(a,fa2)]:
        root=f'/api/dev-account/families/{f}/hira-runs/{run}'
        assert c.get(root).status_code==404
        assert c.post(root+'/save',json={}).status_code==404
        assert c.patch(root+'/intake',json={'record_id':str(uuid4()),'choice':'TAKING'}).status_code==404
    assert process(b,fa).status_code==404
    assert b.get(f'/api/dev-account/families/{fa}/hira-runs').status_code==404
    assert a.get(f'/api/dev-account/families/{fa2}/hira-runs').json()['runs']==[]
    assert b.get(f'/api/dev-account/families/{fb}/hira-runs').json()['runs']==[]
    assert a.post('/api/dev-account/logout').status_code==200
    assert a.get(f'/api/dev-account/families/{fa}/hira-runs').status_code==401


def test_photo_and_hira_storage_have_distinct_tables_lists_and_intake():
    c=account();f=family(c);photo,_=processed(c,f);assert save_photo(c,f,photo['run_id']).status_code==200
    hira=process(c,f).json();saved(c,f,hira['run_id'])
    root=f'/api/dev-account/families/{f}'
    assert c.get(root+'/runs').json()['runs'][0]['id']==photo['run_id']
    assert c.get(root+'/hira-runs').json()['runs'][0]['id']==hira['run_id']
    assert c.get(root+'/runs/'+hira['run_id']).status_code==404
    assert c.get(root+'/hira-runs/'+photo['run_id']).status_code==404
    record=hira['result']['current_intake_states'][0]['medication_record_id']
    assert c.patch(root+'/hira-runs/'+hira['run_id']+'/intake',json={'record_id':record,'choice':'TAKING'}).status_code==200
    assert c.get(root+'/runs/'+photo['run_id']).json()['intake_states'][0]['verification_status']=='PENDING'


def test_v1_database_migration_keeps_photo_accounts_sessions_and_intakes():
    c=account();f=family(c);photo,_=processed(c,f);assert save_photo(c,f,photo['run_id']).status_code==200
    with database() as db:
        baseline={table:[tuple(r) for r in db.execute(f'SELECT * FROM {table}')] for table in ['users','sessions','families','runs','intake']}
        db.execute('DROP TABLE hira_intake');db.execute('DROP TABLE hira_runs');db.execute('PRAGMA user_version=1')
    with database() as db:
        assert db.execute('PRAGMA user_version').fetchone()[0]==2
        assert all([tuple(r) for r in db.execute(f'SELECT * FROM {table}')]==rows for table,rows in baseline.items())
    assert c.get(f'/api/dev-account/families/{f}/runs/{photo["run_id"]}').status_code==200
    assert process(c,f).status_code==200


@pytest.mark.parametrize('name,data,status',[('bad.txt',b'bad',415),('empty.xlsx',b'',400),('bad.xlsx',b'bad',400)])
def test_bad_uploads_do_not_create_a_run(name,data,status):
    c=account();f=family(c)
    response=c.post(f'/api/dev-account/families/{f}/hira/process',files={'previous_file':(name,data),'current_file':('ok.xlsx',_xlsx([known()]))})
    assert response.status_code==status
    with database() as db:assert db.execute('SELECT count(*) FROM hira_runs').fetchone()[0]==0


def test_fake_official_lookup_only_and_csrf_enforced():
    c=account();f=family(c)
    with patch('backend.services.mfds.real_client.RealMfdsClient.search_by_name',side_effect=AssertionError('live forbidden')):
        assert process(c,f).status_code==200
    c.headers.pop('X-CSRF-Token');assert process(c,f).status_code==403
