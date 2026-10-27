"""Protected Gemini bridge tested with the actual SDK and in-memory transport only."""
from contextlib import contextmanager
import json
from unittest.mock import patch
from uuid import uuid4
import httpx
import pytest
from google import genai
from backend.api import gemini_bridge, photo_demo
from backend.tests.test_dev_account import environment, account, family, save
from backend.tests.test_photo_demo import draft
from backend.tests.test_photo_upload import image

_REAL_CLIENT=genai.Client


@contextmanager
def fake_sdk(raw=None,*,status=200,timeout=False):
    calls=[]
    def handler(request):
        calls.append(request)
        assert json.loads(request.content)['generationConfig']['maxOutputTokens']==4096
        if timeout:raise httpx.ReadTimeout('SYNTHETIC-PRIVATE-TEXT',request=request)
        if status!=200:return httpx.Response(status,json={'error':{'code':status,'message':'SYNTHETIC-PRIVATE-TEXT','status':'UNAVAILABLE'}})
        return httpx.Response(200,json={'candidates':[{'content':{'role':'model','parts':[{'text':raw if raw is not None else photo_demo._fixture('single')}]},'finishReason':'STOP'}]})
    def client(*args,**kwargs):
        options=kwargs['http_options'];assert options.timeout==60000 and options.retry_options.attempts==1
        options.client_args.update(transport=httpx.MockTransport(handler),trust_env=False)
        return _REAL_CLIENT(*args,**kwargs)
    with patch.object(genai,'Client',side_effect=client):yield calls


@pytest.fixture(autouse=True)
def live_gate_for_fake_transport(monkeypatch):
    monkeypatch.setenv('YAKEUM_GEMINI_LIVE_ENABLED','1')
    monkeypatch.setenv('YAKEUM_GEMINI_LIVE_MAX_REQUESTS','10')
    monkeypatch.setenv('GEMINI_API_KEY','synthetic-test-key')
    monkeypatch.setenv('YAKEUM_GEMINI_MODEL','synthetic-test-model')
    monkeypatch.setattr(gemini_bridge,'_attempts',0)


def upload(c,f,data=None,name='synthetic.png',mime='image/png'):
    return c.post(f'/api/dev-account/families/{f}/photos/gemini-extract',data={'record_date':'2026-10-27','source_type':'MEDICINE_BAG'},files={'file':(name,image() if data is None else data,mime)})


def body(documents):
    return {'normalization_confirmed':True,**{side:{'document_id':doc['document_id'],'reviews':[{'index':i,'confirmed':v['record'] is not None and v['status']!='FAILED','draft':draft(v['record'])} for i,v in enumerate(doc['results'])]} for side,doc in zip(('previous','current'),documents)}}


def test_real_sdk_fake_transport_to_edit_compare_save_reload_delete_and_ownership():
    c=account();f=family(c)
    with fake_sdk() as calls:
        documents=[upload(c,f).json(),upload(c,f).json()]
        b=body(documents);b['current']['reviews'][0]['draft']['dose']='2'
        response=c.post(f'/api/dev-account/families/{f}/photos/process',json=b)
        result=response.json();assert response.status_code==200
        assert len(calls)==2
    assert result['result']['stage']=='compared'
    assert result['result']['extraction_sources']=={'previous':'GEMINI','current':'GEMINI'}
    assert result['result']['original_results']['current'][0]['record']['user_confirmed'] is False
    assert result['result']['current_intake_states'][0]['verification_status']=='PENDING'
    assert save(c,f,result['run_id']).status_code==200
    path=f'/api/dev-account/families/{f}/runs/{result["run_id"]}'
    assert c.get(path).json()['result']['extraction_sources']['current']=='GEMINI'
    buser=account('synthetic_b');assert buser.get(path).status_code==404
    assert buser.delete(path).status_code==404
    assert c.delete(path).status_code==200 and c.get(path).status_code==404


@pytest.mark.parametrize('scenario',['mixed','empty','json'])
def test_uncertain_or_mixed_results_preserved_and_held(scenario):
    c=account();f=family(c)
    raw=json.loads(photo_demo._fixture('single'))
    if scenario=='mixed':raw['medications'].append({**raw['medications'][0],'dose_per_administration':'읽기불가'})
    if scenario=='empty':raw['medications']=[]
    with fake_sdk('invalid JSON' if scenario=='json' else json.dumps(raw)):
        docs=[upload(c,f).json(),upload(c,f).json()]
    result=c.post(f'/api/dev-account/families/{f}/photos/process',json=body(docs)).json()['result']
    assert result['stage']=='held' and result['reconciliation_result'] is None
    assert result['current_intake_states']==[]
    if scenario=='mixed':
        assert len(docs[0]['results'])==2 and docs[0]['results'][0]['record'] is not None
        assert docs[0]['results'][1]['status']=='FAILED'


@pytest.mark.parametrize('missing',['flag','key','model','budget'])
def test_no_configuration_no_network_no_mock_fallback(monkeypatch,missing):
    c=account();f=family(c)
    if missing=='flag':monkeypatch.delenv('YAKEUM_GEMINI_LIVE_ENABLED')
    if missing=='key':monkeypatch.delenv('GEMINI_API_KEY')
    if missing=='model':monkeypatch.delenv('YAKEUM_GEMINI_MODEL')
    if missing=='budget':monkeypatch.setenv('YAKEUM_GEMINI_LIVE_MAX_REQUESTS','9999')
    with fake_sdk() as calls:response=upload(c,f)
    assert response.status_code==503 and not calls


@pytest.mark.parametrize('timeout',[False,True])
def test_provider_failure_timeout_sanitized_single_attempt(timeout,caplog):
    c=account();f=family(c)
    with fake_sdk(status=503,timeout=timeout) as calls:response=upload(c,f)
    assert response.status_code==200
    result=response.json()['results'];assert result[0]['status']=='FAILED'
    assert len(calls)==1
    assert 'SYNTHETIC-PRIVATE-TEXT' not in response.text+caplog.text
    assert 'synthetic-test-key' not in response.text+caplog.text


def test_budget_stops_more_calls_and_invalid_images_never_call(monkeypatch):
    c=account();f=family(c);monkeypatch.setenv('YAKEUM_GEMINI_LIVE_MAX_REQUESTS','1')
    with fake_sdk() as calls:
        assert upload(c,f,b'bad').status_code==422
        assert upload(c,f).status_code==200
        assert upload(c,f).status_code==429
        assert len(calls)==1


def test_foreign_family_never_reaches_transport():
    c=account();f=family(c);other=account('synthetic_b')
    with fake_sdk() as calls:assert upload(other,f).status_code==404
    assert calls==[]
