"""Synthetic accounts/records only. No external providers or real patient data."""
from copy import deepcopy
import hashlib
import json
from time import time
from unittest.mock import patch
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.api import dev_account
from backend.storage.local_db import database
from backend.tests.test_photo_upload import image
from backend.tests.test_photo_demo import draft

ORIGIN='http://testserver'
PASSWORD='SYNTHETIC-only-pass-123'


@pytest.fixture(autouse=True)
def environment(monkeypatch,tmp_path):
    monkeypatch.setenv('YAKEUM_DEV_ACCOUNT_ENABLED','1')
    monkeypatch.setenv('YAKEUM_APP_MODE','development')
    monkeypatch.setenv('YAKEUM_DEV_ORIGIN',ORIGIN)
    monkeypatch.setenv('YAKEUM_DEV_DB_PATH',str(tmp_path/'accounts.sqlite3'))


def account(username='synthetic_a'):
    c=TestClient(app);c.headers['Origin']=ORIGIN
    assert c.post('/api/dev-account/register',json={'username':username,'password':PASSWORD}).status_code==201
    r=c.post('/api/dev-account/login',json={'username':username,'password':PASSWORD})
    assert r.status_code==200
    c.headers['X-CSRF-Token']=r.json()['csrf_token']
    return c


def family(c,name='가상 가족'):
    r=c.post('/api/dev-account/families',json={'name':name});assert r.status_code==201
    return r.json()['id']


def upload(c,f,scenario='single'):
    r=c.post(f'/api/dev-account/families/{f}/photos/extract',data={'record_date':'2026-10-27','source_type':'MEDICINE_BAG','scenario':scenario},files={'file':('virtual.png',image(),'image/png')})
    assert r.status_code==200,r.text
    return r.json()


def processed(c,f,confirmed=True,scenario='single'):
    documents=[upload(c,f),upload(c,f,scenario)]
    body={'normalization_confirmed':confirmed}
    for side,d in zip(('previous','current'),documents):
        body[side]={'document_id':d['document_id'],'reviews':[{'index':i,'confirmed':r['record'] is not None and r['status']!='FAILED','draft':draft(r['record'])} for i,r in enumerate(d['results'])]}
    body['current']['reviews'][0]['draft']['dose']='2'
    r=c.post(f'/api/dev-account/families/{f}/photos/process',json=body)
    assert r.status_code==200,r.text
    return r.json(),body


def save(c,f,r,choices=None):
    return c.post(f'/api/dev-account/families/{f}/runs/{r}/save',json={'intake_confirmations':choices or []})


def test_persist_original_edited_confirmed_normalized_and_comparison_separately():
    c=account();f=family(c);r,body=processed(c,f)
    assert save(c,f,r['run_id']).status_code==200
    result=c.get(f'/api/dev-account/families/{f}/runs/{r["run_id"]}').json()
    assert result['reviews']==body
    assert result['result']['original_results']['current'][0]['record']['dose_per_administration']=='1'
    assert result['result']['edited_records']['current'][0]['dose_per_administration']=='2'
    assert result['result']['original_results']['current'][0]['record']['user_confirmed'] is False
    assert result['result']['normalization_results']['current'][0]['record']['user_confirmed'] is True
    assert result['result']['reconciliation_result']['items'][0]['status']=='DOSE_CHANGED'
    assert all(s['intake_status']=='UNKNOWN' and s['verification_status']=='PENDING' for s in result['intake_states'])
    # New DB connections and a new browser/session can load saved data after login.
    second=TestClient(app);second.headers['Origin']=ORIGIN
    login=second.post('/api/dev-account/login',json={'username':'synthetic_a','password':PASSWORD})
    assert login.status_code==200
    assert second.get(f'/api/dev-account/families/{f}/runs').json()['runs'][0]['id']==r['run_id']
    assert second.get(f'/api/dev-account/families/{f}/runs/{r["run_id"]}').status_code==200


def test_intake_selection_is_explicit_separate_and_server_attributed():
    c=account();f=family(c);r,_=processed(c,f);record=r['result']['current_intake_states'][0]['medication_record_id']
    assert save(c,f,r['run_id'],[{'record_id':record,'choice':'TAKING'}]).status_code==200
    path=f'/api/dev-account/families/{f}/runs/{r["run_id"]}'
    data=c.get(path).json();state=data['intake_states'][0]
    assert state['intake_status']=='TAKING' and state['verification_status']=='USER_VERIFIED'
    assert state['verified_by'] not in (None,'LOCAL_BROWSER_DEMO')
    assert data['result']['current_intake_states'][0]['verification_status']=='PENDING'
    comparison=deepcopy(data['result']['reconciliation_result'])
    assert c.patch(path+'/intake',json={'record_id':record,'choice':'UNKNOWN'}).status_code==200
    data=c.get(path).json()
    assert data['intake_states'][0]['intake_status']=='UNKNOWN'
    assert data['intake_states'][0]['verification_status']=='USER_VERIFIED'
    assert data['result']['reconciliation_result']==comparison
    assert save(c,f,r['run_id']).status_code==200
    assert len(c.get(f'/api/dev-account/families/{f}/runs').json()['runs'])==1


def test_other_user_and_other_family_read_write_and_document_theft_blocked():
    a=account();b=account('synthetic_b');fa=family(a);fb=family(b);own_other=family(a,'가상 다른 가족')
    r,body=processed(a,fa);assert save(a,fa,r['run_id']).status_code==200
    assert b.get('/api/dev-account/families').json()['families']==[{'id':fb,'name':'가상 가족'}]
    for target in [fa,fb]:
        path=f'/api/dev-account/families/{target}/runs/{r["run_id"]}'
        assert b.get(path).status_code==404
        assert b.post(path+'/save',json={}).status_code==404
        assert b.patch(path+'/intake',json={'record_id':str(uuid4()),'choice':'TAKING'}).status_code==404
    assert a.get(f'/api/dev-account/families/{own_other}/runs/{r["run_id"]}').status_code==404
    assert a.post(f'/api/dev-account/families/{own_other}/photos/process',json=body).status_code==410
    assert b.post(f'/api/dev-account/families/{fb}/photos/process',json=body).status_code==410
    assert b.post(f'/api/dev-account/families/{fa}/photos/extract',data={'record_date':'2026-10-27','source_type':'MEDICINE_BAG'},files={'file':('virtual.png',image(),'image/png')}).status_code==404


def test_logout_invalidates_cookie_and_protected_endpoints():
    c=account();f=family(c);token=c.cookies.get(dev_account.COOKIE)
    assert c.post('/api/dev-account/logout').status_code==200
    c.cookies.set(dev_account.COOKIE,token)
    assert c.get('/api/dev-account/me').status_code==401
    assert c.get(f'/api/dev-account/families/{f}/runs').status_code==401
    assert c.post('/api/dev-account/families',json={'name':'가상'}).status_code==401


def test_session_expiry_and_csrf_origin_protection():
    c=account();f=family(c)
    c.headers.pop('X-CSRF-Token')
    assert c.post('/api/dev-account/families',json={'name':'가상'}).status_code==403
    c.headers['Origin']='https://untrusted.invalid'
    assert c.post('/api/dev-account/login',json={'username':'synthetic_a','password':PASSWORD}).status_code==403
    c.headers.pop('Origin')
    assert c.post('/api/dev-account/register',json={'username':'other','password':PASSWORD}).status_code==403
    with database() as db: db.execute('UPDATE sessions SET expires=?',(time()-1,))
    assert c.get('/api/dev-account/me').status_code==401


@pytest.mark.parametrize('confirmed,scenario',[(False,'single'),(True,'mixed'),(True,'unknown'),(True,'repeat'),(True,'failed')])
def test_unconfirmed_or_held_never_saved_as_confirmed(confirmed,scenario):
    c=account();f=family(c);r,_=processed(c,f,confirmed,scenario)
    assert r['result']['stage']!='compared'
    assert save(c,f,r['run_id']).status_code==409
    assert c.get(f'/api/dev-account/families/{f}/runs').json()['runs']==[]


def test_invalid_intake_record_and_forged_confirmation_are_rejected():
    c=account();f=family(c);r,_=processed(c,f)
    assert save(c,f,r['run_id'],[{'record_id':str(uuid4()),'choice':'TAKING'}]).status_code==422
    assert c.post(f'/api/dev-account/families/{f}/runs/{r["run_id"]}/save',json={'user_confirmed':True}).status_code==422
    assert c.get(f'/api/dev-account/families/{f}/runs').json()['runs']==[]


def test_password_session_cookie_and_database_do_not_store_plain_password():
    c=account();token=c.cookies.get(dev_account.COOKIE)
    with database() as db:
        user=db.execute('SELECT * FROM users').fetchone();session=db.execute('SELECT * FROM sessions').fetchone()
        assert user['password_hash'].startswith('scrypt$') and PASSWORD not in user['password_hash']
        assert session['token_hash']==hashlib.sha256(token.encode()).hexdigest()
        assert token!=session['token_hash']
    response=c.post('/api/dev-account/login',json={'username':'synthetic_a','password':PASSWORD})
    assert 'HttpOnly' in response.headers['set-cookie'] and 'SameSite=strict' in response.headers['set-cookie']
    assert response.headers['cache-control']=='no-store'
    assert c.post('/api/dev-account/login',json={'username':'synthetic_a','password':'SYNTHETIC-wrong-password'}).status_code==401
    error=c.post('/api/dev-account/login',json={'username':'x','password':'private-short'}).text
    assert 'private-short' not in error


def test_rate_limit_and_development_only_configuration(monkeypatch):
    c=TestClient(app);c.headers['Origin']=ORIGIN
    for _ in range(10):assert c.post('/api/dev-account/login',json={'username':'unknown','password':PASSWORD}).status_code==401
    assert c.post('/api/dev-account/login',json={'username':'unknown','password':PASSWORD}).status_code==429
    monkeypatch.setenv('YAKEUM_APP_MODE','production')
    assert c.get('/api/dev-account/me').status_code==503
    monkeypatch.setenv('YAKEUM_APP_MODE','development');monkeypatch.setenv('YAKEUM_DEV_ACCOUNT_ENABLED','0')
    assert c.get('/api/dev-account/me').status_code==503


def test_live_services_are_not_used_and_documents_expire():
    c=account();f=family(c)
    with patch('backend.api.extraction_provider.extract_image_candidates',side_effect=AssertionError('live forbidden')):
        r,body=processed(c,f)
    with database() as db:db.execute('UPDATE documents SET expires=?',(time()-1,))
    assert c.post(f'/api/dev-account/families/{f}/photos/process',json=body).status_code==410


def test_database_version_is_checked_and_private_file_permissions():
    import os
    from backend.storage.local_db import config
    c=account()
    assert os.stat(config()).st_mode & 0o777 == 0o600
    with database() as db: db.execute('PRAGMA user_version=999')
    assert c.get('/api/dev-account/me').status_code==503


def test_login_rotates_session_and_old_session_cannot_be_replayed():
    c=account();old=c.cookies.get(dev_account.COOKIE)
    response=c.post('/api/dev-account/login',json={'username':'synthetic_a','password':PASSWORD})
    assert response.status_code==200 and c.cookies.get(dev_account.COOKIE)!=old
    replay=TestClient(app);replay.cookies.set(dev_account.COOKIE,old,path='/api/dev-account')
    assert replay.get('/api/dev-account/me').status_code==401


def test_two_sessions_cannot_use_each_others_csrf():
    a=account();b=account('synthetic_b')
    b.headers['X-CSRF-Token']=a.headers['X-CSRF-Token']
    assert b.post('/api/dev-account/families',json={'name':'가상 가족'}).status_code==403


def test_fresh_python_process_can_read_saved_sqlite_state():
    import subprocess
    import sys
    c=account();f=family(c);r,_=processed(c,f)
    assert save(c,f,r['run_id']).status_code==200
    script='''
import json,sys
from backend.storage.local_db import database
with database() as db:
 row=db.execute("SELECT result FROM runs WHERE id=? AND saved=1",(sys.argv[1],)).fetchone()
 value=json.loads(row['result'])
 print(json.dumps({'dose':value['edited_records']['current'][0]['dose_per_administration'],'original_confirmed':value['original_results']['current'][0]['record']['user_confirmed']}))
'''
    value=json.loads(subprocess.check_output([sys.executable,'-c',script,r['run_id']],text=True))
    assert value=={'dose':'2','original_confirmed':False}


@pytest.mark.parametrize('path',['','relative.sqlite3','/workspace/yakeum/frontend/public/unsafe.sqlite3'])
def test_missing_relative_and_repository_db_path_rejected(monkeypatch,path):
    from pathlib import Path
    if path.startswith('/workspace/yakeum'):
        path=str(Path(__file__).resolve().parents[2]/'frontend/public/unsafe.sqlite3')
    monkeypatch.setenv('YAKEUM_DEV_DB_PATH',path)
    assert TestClient(app).get('/api/dev-account/me').status_code==503
