from copy import deepcopy
from dataclasses import replace
from io import BytesIO
from unittest.mock import patch
from uuid import UUID
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from backend.api.main import app
from backend.api import photo_upload as upload
from backend.tests.test_photo_demo import payload, draft

FAMILY='00000000-0000-4000-8000-000000000001'
OTHER='00000000-0000-4000-8000-000000000002'
client=TestClient(app)


def image(fmt='PNG'):
    data=BytesIO();Image.new('RGB',(20,20),'white').save(data,format=fmt);return data.getvalue()


@pytest.fixture(autouse=True)
def empty_store():
    upload.store=upload.SnapshotStore()


def extract(scenario='single',data=None,name='virtual.png',mime='image/png',family=FAMILY):
    return client.post('/api/local-demo/photo-uploads/extract',data={'family_member_id':family,'record_date':'2026-10-27','source_type':'MEDICINE_BAG','scenario':scenario},files={'file':(name,image() if data is None else data,mime)})


def body(previous,current,confirmed=False):
    b=payload(confirmed=confirmed)
    return {'family_member_id':FAMILY,'normalization_confirmed':confirmed,
            **{side:{'upload_token':token,'reviews':b[side]['reviews']} for side,token in [('previous',previous),('current',current)]}}


def process(b):
    return client.post('/api/local-demo/photo-uploads/process',json=b)


def test_upload_edit_normalize_compare_intake_separate_snapshot():
    with patch.object(upload,'fake_response',wraps=upload.fake_response) as fake:
        previous=extract().json();current=extract().json()
        b=body(previous['upload_token'],current['upload_token'])
        b['current']['reviews'][0]['draft']['dose']='2'
        preview=process(b).json()
        assert preview['stage']=='normalized' and preview['reconciliation_result'] is None
        result=process({**b,'normalization_confirmed':True}).json()
        assert fake.call_count==2  # never re-extract while processing edits
    assert result['stage']=='compared'
    assert result['reconciliation_result']['items'][0]['status']=='DOSE_CHANGED'
    assert result['original_results']['current'][0]['record']['dose_per_administration']=='1'
    assert result['edited_records']['current'][0]['dose_per_administration']=='2'
    assert all(r['record']['user_confirmed'] is False for r in result['original_results']['current'])
    assert result['current_intake_states'][0]['intake_status']=='UNKNOWN'
    assert result['current_intake_states'][0]['verification_status']=='PENDING'
    assert result['response_version']==upload.VERSION


@pytest.mark.parametrize('scenario',['mixed','missing','failed','repeat','unknown'])
def test_bad_candidates_preserved_and_comparison_held(scenario):
    p=extract().json();c=extract(scenario).json()
    b=body(p['upload_token'],c['upload_token'],True)
    b['current']['reviews']=[{'index':n,'confirmed':r['record'] is not None and r['status']!='FAILED','draft':draft(r['record'])} for n,r in enumerate(c['results'])]
    if scenario=='missing':
        b['current']['reviews'][1]['draft']['product']='가상알파정'
    result=process(b).json()
    assert result['stage']=='held' and result['pending_decisions']
    assert result['reconciliation_result'] is None and result['current_intake_states']==[]
    assert result['original_results']['current']==c['results']
    if scenario=='mixed':
        assert len(c['results'])==2 and c['results'][0]['record'] is not None
        assert c['results'][1]['status']=='FAILED'


def test_unconfirmed_and_same_document_held():
    p=extract().json();c=extract().json();b=body(p['upload_token'],c['upload_token'],True)
    b['current']['reviews'][0]['confirmed']=False
    assert process(b).json()['stage']=='held'
    b['current']=deepcopy(b['previous'])
    assert process(b).json()['stage']=='held'


def test_missing_duplicate_indices_cannot_skip_candidates():
    p=extract().json();c=extract('multiple').json();b=body(p['upload_token'],c['upload_token'],True)
    assert process(b).json()['stage']=='held'
    b['current']['reviews']*=2
    assert process(b).json()['stage']=='held'


def test_family_and_expiry_rejected_and_reupload_is_new_document():
    p=extract().json();c=extract().json()
    assert p['document_id']!=c['document_id']
    b=body(p['upload_token'],c['upload_token'],True);b['family_member_id']=OTHER
    assert process(b).status_code==410
    upload.store._documents[p['upload_token']]=replace(upload.store._documents[p['upload_token']],expires=0)
    assert process(body(p['upload_token'],c['upload_token'])).status_code==410


@pytest.mark.parametrize('data,name,mime,status',[
    (b'', 'virtual.png','image/png',400),
    (b'bad','virtual.png','image/png',422),
    (image(),'virtual.jpg','image/jpeg',415),
    (image(),'virtual.png','image/jpeg',415),
    (image(),'virtual.svg','image/svg+xml',415),
    (b'x'*(10*1024*1024+1),'virtual.png','image/png',413),
])
def test_invalid_images(data,name,mime,status):
    response=extract(data=data,name=name,mime=mime)
    assert response.status_code==status
    assert isinstance(response.json()['detail'],str)
    assert not upload.store._documents


@pytest.mark.parametrize('fmt,name,mime',[('PNG','virtual.png','image/png'),('JPEG','virtual.jpg','image/jpeg'),('WEBP','virtual.webp','image/webp')])
def test_allowed_formats(fmt,name,mime):
    assert extract(data=image(fmt),name=name,mime=mime).status_code==200


def test_store_bounded_no_raw_images_and_results_are_copied(monkeypatch):
    monkeypatch.setattr(upload,'MAX_DOCUMENTS',1)
    p=extract().json()
    assert extract().status_code==503
    snap=upload.store.get(UUID(p['upload_token']),UUID(FAMILY))
    assert not hasattr(snap,'image')
    snap.results.clear()
    assert upload.store.get(UUID(p['upload_token']),UUID(FAMILY)).results


def test_large_pixels_and_animation_rejected(monkeypatch):
    monkeypatch.setattr(upload,'MAX_PIXELS',100)
    assert extract().status_code==422
    monkeypatch.setattr(upload,'MAX_PIXELS',20_000_000)
    data=BytesIO();Image.new('RGB',(20,20),'red').save(data,format='PNG',save_all=True,append_images=[Image.new('RGB',(20,20),'blue')],duration=100)
    assert extract(data=data.getvalue()).status_code==422


@pytest.mark.parametrize('field',['dose','perDay'])
def test_comparison_required_fields_missing_do_not_mean_maintained(field):
    p=extract().json();c=extract().json();b=body(p['upload_token'],c['upload_token'],True)
    b['current']['reviews'][0]['draft'][field]=''
    if field=='dose': b['current']['reviews'][0]['draft']['doseUnit']=''
    result=process(b).json()
    assert result['stage']=='held'
    assert result['reconciliation_result'] is None


def test_failed_new_upload_does_not_modify_prior_snapshot():
    p=extract().json();before=upload.store.get(UUID(p['upload_token']),UUID(FAMILY))
    assert extract(data=b'corrupt').status_code==422
    assert upload.store.get(UUID(p['upload_token']),UUID(FAMILY))==before


def test_no_external_provider_even_with_live_settings(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','synthetic-unused-key')
    monkeypatch.setenv('YAKEUM_GEMINI_MODEL','synthetic-unused-model')
    with patch('backend.api.extraction_provider.extract_image_candidates', side_effect=AssertionError('live forbidden')):
        assert extract().status_code==200


def test_multiple_candidates_all_reach_normalization_and_timeline():
    p=extract('multiple').json();c=extract('multiple').json();b=body(p['upload_token'],c['upload_token'],True)
    for side, document in [('previous',p),('current',c)]:
        b[side]['reviews']=[{'index':n,'confirmed':True,'draft':draft(r['record'])} for n,r in enumerate(document['results'])]
    result=process(b).json()
    assert result['stage']=='compared'
    assert len(result['reconciliation_result']['items'])==2
    assert len(result['normalization_results']['current'][1]['record']['ingredients'])==2


def test_uploaded_bytes_and_mime_are_passed_to_fake_transport_once():
    data=image('JPEG')
    with patch.object(upload,'fake_response',wraps=upload.fake_response) as transport:
        assert extract(data=data,name='virtual.jpg',mime='image/jpeg').status_code==200
        assert transport.call_count==1
        assert transport.call_args.args[:2]==(data,'image/jpeg')
