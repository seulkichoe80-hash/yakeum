"""Synthetic users/DB/HTTP only; no external medical API requests."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from io import BytesIO
import json
import threading
import urllib.error
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api import mfds_admin
from backend.storage.local_db import database
from backend.services.mfds.tests.test_sample_mapping import xml
from backend.tests.test_dev_account import account, ORIGIN

BASE='/api/dev-account/admin/mfds-probe'


@pytest.fixture(autouse=True)
def setup(monkeypatch,tmp_path):
    monkeypatch.setenv('YAKEUM_DEV_ACCOUNT_ENABLED','1')
    monkeypatch.setenv('YAKEUM_APP_MODE','development')
    monkeypatch.setenv('YAKEUM_DEV_ORIGIN',ORIGIN)
    monkeypatch.setenv('YAKEUM_DEV_DB_PATH',str(tmp_path/'admin.sqlite3'))
    monkeypatch.setenv('YAKEUM_STORAGE_BACKEND','sqlite')
    monkeypatch.setenv('YAKEUM_MFDS_PROBE_ENABLED','1')
    monkeypatch.setenv('YAKEUM_MFDS_PROBE_ADMIN_USERNAME','synthetic_admin')
    monkeypatch.setenv('MFDS_API_KEY','SYNTHETIC-SECRET')
    monkeypatch.setattr(mfds_admin.probe,'fetch_xml',lambda *a:pytest.fail('external call forbidden'))


def admin():return account('synthetic_admin')


def execute(c,**kwargs):return c.post(BASE+'/execute',json={'confirm':True},**kwargs)


def test_unauthenticated_and_non_admin_cannot_view_read_or_execute():
    for client,expected in [(TestClient(app),401),(account('synthetic_other'),403)]:
        client.headers['Origin']=ORIGIN
        for path in ('/view','/status'):
            assert client.get(BASE+path).status_code==expected
        assert execute(client).status_code==expected
    with database() as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE name='mfds_probe_attempts'").fetchone() is None


def test_disabled_missing_or_wrong_admin_is_closed(monkeypatch):
    c=admin()
    for name in ('','synthetic_other','INVALID / USER'):
        monkeypatch.setenv('YAKEUM_MFDS_PROBE_ADMIN_USERNAME',name)
        assert c.get(BASE+'/view').status_code==403
        assert execute(c).status_code==403
    monkeypatch.setenv('YAKEUM_MFDS_PROBE_ENABLED','0')
    assert c.get(BASE+'/status').status_code==404
    assert execute(c).status_code==404


def test_origin_csrf_explicit_confirmation_and_no_arbitrary_query():
    c=admin()
    assert execute(c,headers={'Origin':'https://evil.invalid'}).status_code==403
    assert execute(c,headers={'X-CSRF-Token':'wrong'}).status_code==403
    for body in ({'confirm':False},{'confirm':'true'},{'confirm':True,'name':'other'},{}):
        assert c.post(BASE+'/execute',json=body).status_code==422
    assert c.get(BASE+'/status').json()['consumed'] is False


def test_key_preflight_does_not_consume_budget(monkeypatch):
    c=admin()
    for key in ('','SYNTHETIC%2BKEY'):
        monkeypatch.setenv('MFDS_API_KEY',key)
        assert execute(c).status_code==503
        assert c.get(BASE+'/status').json()['consumed'] is False


def test_success_fixed_query_persisted_and_replayed_after_new_session(monkeypatch):
    c=admin();calls=[]
    def fake(key,name,page,rows):
        calls.append((name,page,rows))
        # The started marker is committed and visible through another connection.
        with database() as db:
            row=db.execute('SELECT * FROM mfds_probe_attempts').fetchone()
            assert row is not None and row['result'] is None
        return xml(3,7)
    monkeypatch.setattr(mfds_admin.probe,'fetch_xml',fake)
    first=execute(c);assert first.status_code==200
    body=first.json();assert body['consumed'] and body['state']=='FINISHED'
    assert body['result']['api_success'] and body['result']['xml_valid']
    assert body['result']['total_count']==7 and body['result']['received_count']==3
    assert body['result']['all_candidates_received'] is False
    assert calls==[('타이레놀',1,3)]
    assert execute(c).json()==body
    # New app/session/DB connection, same file (restart semantics).
    c.post('/api/dev-account/logout')
    other=TestClient(app);other.headers['Origin']=ORIGIN
    login=other.post('/api/dev-account/login',json={'username':'synthetic_admin','password':'SYNTHETIC-only-pass-123'})
    other.headers['X-CSRF-Token']=login.json()['csrf_token']
    assert other.get(BASE+'/status').json()==body
    assert execute(other).json()==body and len(calls)==1
    assert 'SYNTHETIC-SECRET' not in json.dumps(body)


def test_simultaneous_requests_only_one_external_attempt(monkeypatch):
    c=admin();entered=threading.Event();release=threading.Event();calls=[]
    def fake(*args):
        calls.append(True);entered.set();assert release.wait(5);return xml(3,7)
    monkeypatch.setattr(mfds_admin.probe,'fetch_xml',fake)
    headers=dict(c.headers);cookies=dict(c.cookies)
    def send():
        with TestClient(app) as other:
            other.headers.update(headers);other.cookies.update(cookies)
            return execute(other)
    with ThreadPoolExecutor(max_workers=4) as pool:
        first=pool.submit(send);assert entered.wait(5)
        pending=[pool.submit(send) for _ in range(3)]
        responses=[r.result(timeout=5) for r in pending]
        assert all(r.status_code==200 and r.json()['state']=='STARTED_OR_UNCERTAIN' for r in responses)
        release.set();assert first.result(timeout=5).json()['state']=='FINISHED'
    assert calls==[True]


def test_http503_sanitized_saved_once_and_never_retried(monkeypatch,caplog):
    c=admin();calls=[]
    def fake(*args):
        calls.append(True)
        raise urllib.error.HTTPError('https://private.invalid?serviceKey=SYNTHETIC-SECRET',503,'private',
            {'Content-Type':'text/plain','Server':'envoy','Set-Cookie':'SYNTHETIC-SECRET'},
            BytesIO(b'upstream connect error SYNTHETIC-SECRET https://private.invalid'))
    monkeypatch.setattr(mfds_admin.probe,'fetch_xml',fake)
    result=execute(c).json()
    assert result['result']['http_status']==503
    assert result['result']['diagnostic_headers']['server']=='envoy'
    assert result['result']['body_signals']==['UPSTREAM_CONNECT_ERROR_TEXT']
    assert execute(c).json()==result and calls==[True]
    with database() as db: stored=db.execute('SELECT result FROM mfds_probe_attempts').fetchone()[0]
    assert 'SYNTHETIC-SECRET' not in stored+json.dumps(result)+caplog.text
    assert 'https://private.invalid' not in stored


def test_process_crash_leaves_consumed_record_and_blocks_restart(monkeypatch):
    c=admin()
    def crash(*args):raise KeyboardInterrupt()
    monkeypatch.setattr(mfds_admin.probe,'live_result',crash)
    # Call coordinator directly to model process termination without ASGI teardown noise.
    with pytest.raises(KeyboardInterrupt):
        mfds_admin.execute(mfds_admin.ExecuteInput(confirm=True),{})
    monkeypatch.setattr(mfds_admin.probe,'live_result',lambda *a:pytest.fail('retry forbidden'))
    assert c.get(BASE+'/status').json()['state']=='STARTED_OR_UNCERTAIN'
    assert execute(c).json()['state']=='STARTED_OR_UNCERTAIN'


def test_claim_commit_failure_makes_no_request(monkeypatch):
    c=admin();original=mfds_admin.database
    @contextmanager
    def fail():
        with original() as db:
            yield db
            raise RuntimeError('synthetic commit failure')
    monkeypatch.setattr(mfds_admin,'database',fail)
    with pytest.raises(RuntimeError):mfds_admin.execute(mfds_admin.ExecuteInput(confirm=True),{})
    monkeypatch.setattr(mfds_admin,'database',original)
    assert c.get(BASE+'/status').json()['consumed'] is False


def test_result_persist_failure_never_reissues_request(monkeypatch):
    c=admin();original=mfds_admin.database;calls=[];count=0
    @contextmanager
    def fail_second():
        nonlocal count
        count+=1
        if count==2:raise RuntimeError('synthetic DB unavailable')
        with original() as db:yield db
    monkeypatch.setattr(mfds_admin,'database',fail_second)
    monkeypatch.setattr(mfds_admin.probe,'fetch_xml',lambda *a:(calls.append(True) or xml(3,7)))
    with pytest.raises(RuntimeError):mfds_admin.execute(mfds_admin.ExecuteInput(confirm=True),{})
    monkeypatch.setattr(mfds_admin,'database',original)
    assert c.get(BASE+'/status').json()['state']=='STARTED_OR_UNCERTAIN'
    assert execute(c).json()['state']=='STARTED_OR_UNCERTAIN' and calls==[True]


def test_page_security_logout_and_feature_toggle_preserve_budget(monkeypatch):
    c=admin();page=c.get(BASE+'/view')
    assert page.status_code==200 and 'MFDS_API_KEY' not in page.text
    assert page.headers['cache-control']=='no-store'
    assert "frame-ancestors 'none'" in page.headers['content-security-policy']
    monkeypatch.setattr(mfds_admin.probe,'fetch_xml',lambda *a:xml(3,7))
    assert execute(c).json()['consumed']
    monkeypatch.setenv('YAKEUM_MFDS_PROBE_ENABLED','0')
    assert c.get(BASE+'/status').status_code==404
    monkeypatch.setenv('YAKEUM_MFDS_PROBE_ENABLED','1')
    assert execute(c).json()['consumed']
    c.post('/api/dev-account/logout')
    assert c.get(BASE+'/view').status_code==401 and execute(c).status_code==401


@pytest.mark.parametrize('problem',['timeout','malformed_xml'])
def test_uncertain_response_consumes_once_without_retry(monkeypatch,problem):
    c=admin();calls=[]
    def fake(*args):
        calls.append(True)
        if problem=='timeout':raise TimeoutError('SYNTHETIC-SECRET')
        return 'invalid XML SYNTHETIC-SECRET'
    monkeypatch.setattr(mfds_admin.probe,'fetch_xml',fake)
    first=execute(c).json()
    assert first['state']=='FINISHED' and first['result']['error']
    assert execute(c).json()==first and calls==[True]
    assert 'SYNTHETIC-SECRET' not in json.dumps(first)


def test_external_demo_rejects_ephemeral_sqlite_budget(monkeypatch):
    from fastapi import HTTPException
    monkeypatch.setenv('YAKEUM_EXTERNAL_DEMO','1')
    with pytest.raises(HTTPException) as exc:
        mfds_admin.administrator({'username':'synthetic_admin'})
    assert exc.value.status_code==503
