"""Read-only recovery of owned processing snapshots; synthetic records only."""
from copy import deepcopy
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.storage.local_db import database
from backend.tests.test_dev_account import environment, account, family, ORIGIN
from backend.tests.test_account_hira import process, saved
from backend.tests.test_b_d_c_api import _row


def test_recover_unsaved_then_save_without_reprocessing():
    c=account();f=family(c);original=process(c,f).json();run=original['run_id'];root=f'/api/dev-account/families/{f}'
    assert c.get(root+'/hira-runs').json()['runs']==[]
    with patch('backend.services.mfds.probe.fetch_xml',side_effect=AssertionError('external forbidden')),patch(
        'backend.api.pipeline.process_hira_comparison',side_effect=AssertionError('reprocessing forbidden')):
        assert c.get(root+'/hira-drafts').json()['drafts'][0]['id']==run
        restored=c.get(root+'/hira-drafts/'+run)
        assert restored.status_code==200 and restored.json()==original
        with database() as db:
            assert db.execute('SELECT saved FROM hira_runs WHERE id=?',(run,)).fetchone()[0]==0
            assert db.execute('SELECT count(*) FROM hira_intake WHERE run_id=?',(run,)).fetchone()[0]==0
        result=saved(c,f,run)
        assert result['result']==original['result'] and result['saved'] is True
        assert all(s['verification_status']=='PENDING' for s in result['intake_states'])
        assert c.get(root+'/hira-drafts').json()['drafts']==[]
        assert c.get(root+'/hira-drafts/'+run).status_code==404
        assert c.get(root+'/hira-runs/'+run).status_code==200


def test_draft_reads_require_session_owner_and_family():
    a=account();f=family(a);other_family=family(a,'다른 가상 가족');b=account('synthetic_b');fb=family(b)
    run=process(a,f).json()['run_id'];root=f'/api/dev-account/families/{f}/hira-drafts'
    assert b.get(root).status_code==404 and b.get(root+'/'+run).status_code==404
    assert a.get(f'/api/dev-account/families/{other_family}/hira-drafts/'+run).status_code==404
    assert b.get(f'/api/dev-account/families/{fb}/hira-drafts/'+run).status_code==404
    assert a.get(root+'/'+str(uuid4())).status_code==404
    assert TestClient(app).get(root).status_code==401
    a.post('/api/dev-account/logout')
    assert a.get(root).status_code==401 and a.get(root+'/'+run).status_code==401


@pytest.mark.parametrize('empty',[False,True])
def test_held_null_and_executed_zero_recover_without_changing_meaning(empty):
    c=account();f=family(c)
    rows=[] if empty else [_row(1,'2026-10-01','가상미등록약','000000001')]
    original=process(c,f,previous=rows,current=rows).json();run=original['run_id']
    before=deepcopy(original)
    restored=c.get(f'/api/dev-account/families/{f}/hira-drafts/{run}').json()
    assert restored==before
    r=restored['result']
    if empty:assert r['comparison']['executed'] is True and r['reconciliation_result']['items']==[]
    else:assert r['comparison']['executed'] is False and r['reconciliation_result'] is None and r['source_rows']
    assert restored['intake_states']==[]
