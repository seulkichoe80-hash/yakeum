"""No external transport; real persistent local transactions and protected routes."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from backend.api import gemini_synthetic as gate
from backend.tests.test_dev_account import environment, account, family
from backend.tests.test_gemini_account import fake_sdk
from backend.services.extraction import ExtractionContext

IMAGE=Path(__file__).resolve().parents[2]/'docs/integration/samples/render-gemini/synthetic-bag.png'

@pytest.fixture
def setup(environment,monkeypatch):
    monkeypatch.setenv('YAKEUM_GEMINI_SYNTHETIC_ENABLED','1')
    monkeypatch.setenv('YAKEUM_GEMINI_SYNTHETIC_ADMIN_USERNAME','synthetic_a')
    monkeypatch.setenv('GEMINI_API_KEY','SYNTHETIC-ONLY')
    monkeypatch.setenv('YAKEUM_GEMINI_MODEL','synthetic-model')
    monkeypatch.setenv('YAKEUM_GEMINI_LIVE_ENABLED','0')
    return monkeypatch


def post(c,f,side='previous',consent=True,data=None):
    return c.post(f'/api/dev-account/families/{f}/photos/gemini-extract',
      data={'record_date':'2026-10-01','source_type':'MEDICINE_BAG','synthetic_consent':str(consent).lower(),'synthetic_side':side},
      files={'file':('synthetic.png',IMAGE.read_bytes() if data is None else data,'image/png')})


def test_protected_route_two_global_slots_and_no_replay(setup):
    c=account();f=family(c)
    with fake_sdk() as calls:
        assert post(c,f).status_code==200
        assert post(c,f).status_code==409
        assert post(c,f,'current').status_code==200
        assert post(c,family(c),'current').status_code==409
        assert len(calls)==2
    # New client/session does not reset persisted slots.
    from fastapi.testclient import TestClient
    from backend.api.main import app
    c2=TestClient(app);c2.headers.update(c.headers);c2.cookies.update(c.cookies)
    assert post(c2,f).status_code==409


def test_permission_consent_hash_ownership_and_csrf(setup):
    c=account();f=family(c);other=account('synthetic_b');foreign=family(other)
    with fake_sdk() as calls:
        assert post(other,foreign).status_code==403
        assert post(other,f).status_code==404
        # Explicit consent alone is never administrator permission.
        assert post(c,f,consent=False).status_code==503  # generic live mode remains off
        from backend.tests.test_photo_upload import image
        assert post(c,f,data=image()).status_code==422
        token=c.headers.pop('X-CSRF-Token');assert post(c,f).status_code==403;c.headers['X-CSRF-Token']=token
        assert len(calls)==0


def test_external_never_uses_general_bridge(setup):
    c=account();f=family(c)
    setup.setenv('YAKEUM_EXTERNAL_DEMO','1')
    # This route test uses local DB; external requires durable PostgreSQL.
    with fake_sdk() as calls:
        assert post(c,f).status_code==503
        assert len(calls)==0


@pytest.mark.parametrize('timeout',[False,True])
def test_failure_consumes_slot(setup,timeout):
    c=account();f=family(c)
    with fake_sdk(status=503,timeout=timeout) as calls:
        assert post(c,f).status_code==200
        assert post(c,f).status_code==409
        assert len(calls)==1


def test_simultaneous_claim_and_crash_persist(setup):
    def attempt():
        try:
            return gate.extract(IMAGE.read_bytes(),'image/png',None,{'username':'synthetic_a'},True,'previous')
        except HTTPException as e:return e.status_code
    with patch.object(gate,'extract_image_candidates',return_value=[]) as transport:
        with ThreadPoolExecutor(2) as pool:results=list(pool.map(lambda _:attempt(),range(2)))
        assert results.count(409)==1 and transport.call_count==1
    with patch.object(gate,'extract_image_candidates',side_effect=RuntimeError('synthetic crash')):
        with pytest.raises(RuntimeError):gate.extract(IMAGE.read_bytes(),'image/png',None,{'username':'synthetic_a'},True,'current')
    with patch.object(gate,'extract_image_candidates') as transport:
        with pytest.raises(HTTPException) as error:gate.extract(IMAGE.read_bytes(),'image/png',None,{'username':'synthetic_a'},True,'current')
        assert error.value.status_code==409 and not transport.called


def test_disabled_missing_key_and_anonymous_never_call(setup):
    from fastapi.testclient import TestClient
    from backend.api.main import app
    c=account();f=family(c)
    anonymous=TestClient(app);anonymous.headers['Origin']='http://testserver'
    with fake_sdk() as calls:
        assert post(anonymous,f).status_code==401
        setup.setenv('YAKEUM_GEMINI_SYNTHETIC_ENABLED','0')
        assert post(c,f).status_code==404
        setup.setenv('YAKEUM_GEMINI_SYNTHETIC_ENABLED','1')
        setup.setenv('GEMINI_API_KEY','')
        assert post(c,f).status_code==503
        assert not calls


def test_commit_failure_never_starts_provider(setup):
    from contextlib import contextmanager
    from backend.storage.local_db import database
    @contextmanager
    def uncertain_commit():
        with database() as db:
            yield db
            raise RuntimeError('synthetic failed commit')
    with patch.object(gate,'database',uncertain_commit), patch.object(gate,'extract_image_candidates') as transport:
        with pytest.raises(RuntimeError):gate.extract(IMAGE.read_bytes(),'image/png',None,{'username':'synthetic_a'},True,'previous')
        assert not transport.called


def test_new_python_process_cannot_reset_consumption(setup):
    import os,subprocess,sys
    with patch.object(gate,'extract_image_candidates',return_value=[]):
        gate.extract(IMAGE.read_bytes(),'image/png',None,{'username':'synthetic_a'},True,'previous')
    script='''from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException
from backend.api import gemini_synthetic as g
with patch.object(g,'extract_image_candidates',side_effect=AssertionError('network forbidden')):
 try:g.extract(Path('docs/integration/samples/render-gemini/synthetic-bag.png').read_bytes(),'image/png',None,{'username':'synthetic_a'},True,'previous')
 except HTTPException as e:assert e.status_code==409
 else:raise AssertionError('consumed slot was reopened')
'''
    result=subprocess.run([sys.executable,'-c',script],env=os.environ.copy(),capture_output=True,text=True)
    assert result.returncode==0,result.stderr
