import json
from unittest.mock import patch

import pytest

from backend.services.mfds.probe import inspect_xml, main, ProbeError
from backend.services.mfds.tests.test_sample_mapping import xml


def test_default_never_calls_and_key_not_printed(monkeypatch, capsys):
    monkeypatch.setenv('MFDS_API_KEY','SYNTHETIC-SECRET')
    with patch('urllib.request.urlopen',side_effect=AssertionError('no live')):
        assert main([],transport=lambda *a: pytest.fail('called')) == 0
    out=capsys.readouterr().out
    assert 'SYNTHETIC-SECRET' not in out
    assert json.loads(out)['request_attempts']==0 and json.loads(out)['key_registered'] is True


def test_injected_live_one_attempt_partial_page_no_unique(monkeypatch,capsys):
    monkeypatch.setenv('MFDS_API_KEY','SYNTHETIC-SECRET')
    calls=[]
    def fake(*args):
        calls.append(True);return xml(3,7)
    assert main(['--live'],transport=fake)==0
    out=json.loads(capsys.readouterr().out)
    assert calls==[True] and out['request_attempts']==1
    assert out['all_candidates_received'] is False and out['unique_candidate_evidence'] is False
    assert out['next_page_available'] is True and out['automatic_next_page_requests']==0
    assert 'SYNTHETIC-SECRET' not in str(out)


def test_failure_no_retry_or_sensitive_exception(monkeypatch,capsys):
    monkeypatch.setenv('MFDS_API_KEY','SYNTHETIC-SECRET')
    calls=[]
    def fake(*args):
        calls.append(True);raise RuntimeError('SYNTHETIC-SECRET keyed URL and private contents')
    assert main(['--live'],transport=fake)==1
    out=capsys.readouterr().out
    assert calls==[True] and 'SYNTHETIC-SECRET' not in out and 'private' not in out
    assert json.loads(out)['error']=='TRANSPORT_OR_FILE_FAILURE'


def test_missing_key_no_attempt(monkeypatch,capsys):
    monkeypatch.delenv('MFDS_API_KEY',raising=False)
    assert main(['--live'],transport=lambda *a: pytest.fail('called'))==1
    out=json.loads(capsys.readouterr().out)
    assert out['request_attempts']==0 and out['error']=='KEY_MISSING'


def test_complete_single_candidate_still_not_ingredient_verification():
    out=inspect_xml(xml(1,1))
    assert out['all_candidates_received'] and out['unique_candidate_evidence']
    assert out['ingredient_strength_verified_against_user_record'] is False
    assert out['products'][0]['direct_amount_count']==1
    assert out['products'][0]['insurance_code_known'] is False


def test_last_page_not_entire_dataset():
    out=inspect_xml(xml(1,7).replace('<pageNo>1','<pageNo>3'),page=3)
    assert not out['all_candidates_received'] and not out['next_page_available']
    assert not out['unique_candidate_evidence']


@pytest.mark.parametrize('text,error',[
    ('broken','XML_OR_MAPPING_INVALID'),
    (xml(1,7),'PAGE_ROW_COUNT_MISMATCH'),
    (xml().replace('<totalCount>1','<totalCount>unknown'),'PAGINATION_INVALID'),
    (xml().replace('<pageNo>1','<pageNo>2'),'PAGINATION_MISMATCH'),
    (xml().replace('<resultCode>00','<resultCode>30'),'API_RESULT_NOT_SUCCESS'),
    (xml().replace('<ITEM_NAME>','<OTHER_NAME>').replace('</ITEM_NAME>','</OTHER_NAME>'),'PRODUCT_FIELDS_INVALID'),
])
def test_bad_responses_fail_safely(text,error):
    with pytest.raises(ProbeError,match=error):inspect_xml(text)


def test_empty_success_distinct_from_failed_or_partial():
    result=inspect_xml(xml(0,0))
    assert result['all_candidates_received'] and not result['unique_candidate_evidence']
    assert result['received_count']==0 and result['products']==[]


def test_offline_file_ignores_live_transport(tmp_path,capsys):
    path=tmp_path/'virtual.xml';path.write_text(xml(3,7))
    assert main(['--xml',str(path)],transport=lambda *a:pytest.fail('called'))==0
    out=json.loads(capsys.readouterr().out)
    assert out['mode']=='offline' and out['request_attempts']==0


def test_live_transport_xml_params_tls_timeout_and_no_redirect(monkeypatch):
    import urllib.parse
    from unittest.mock import MagicMock
    from backend.services.mfds.probe import fetch_xml, NoRedirect
    monkeypatch.setenv('SSL_CERT_FILE','/synthetic/ca.pem')
    opener=MagicMock()
    opener.open.return_value.__enter__.return_value.read.return_value=xml().encode()
    with patch('backend.services.mfds.probe.ssl.create_default_context') as tls, patch(
        'backend.services.mfds.probe.urllib.request.build_opener',return_value=opener):
        assert fetch_xml('SYNTHETIC-SECRET','가상제품',1,3)==xml()
        tls.assert_called_once_with(cafile='/synthetic/ca.pem')
    assert opener.open.call_count==1
    req=opener.open.call_args.args[0]
    query=urllib.parse.parse_qs(urllib.parse.urlsplit(req.full_url).query)
    assert query['type']==['xml'] and query['serviceKey']==['SYNTHETIC-SECRET']
    assert query['numOfRows']==['3'] and query['pageNo']==['1']
    assert opener.open.call_args.kwargs['timeout']==15
    assert NoRedirect().redirect_request(None,None,302,None,None,'https://example.invalid') is None


def test_sensitive_http_exception_is_sanitized(monkeypatch,capsys):
    import urllib.error
    monkeypatch.setenv('MFDS_API_KEY','SYNTHETIC-SECRET')
    def fake(*a):
        raise urllib.error.HTTPError('https://example.invalid?serviceKey=SYNTHETIC-SECRET',403,'SYNTHETIC-SECRET',{},None)
    assert main(['--live'],transport=fake)==1
    out=capsys.readouterr().out
    assert 'SYNTHETIC-SECRET' not in out
    assert json.loads(out)['http_status']==403 and json.loads(out)['request_attempts']==1


def test_endpoint_exact_parameters_and_single_key_encoding(monkeypatch):
    from unittest.mock import MagicMock
    from urllib.parse import urlsplit, parse_qs
    from backend.services.mfds.probe import fetch_xml
    opener=MagicMock()
    opener.open.return_value.__enter__.return_value.read.return_value=xml().encode()
    with patch('backend.services.mfds.probe.ssl.create_default_context'), patch(
        'backend.services.mfds.probe.urllib.request.build_opener',return_value=opener):
        fetch_xml('SYNTHETIC+a/b=','타이레놀',1,3)
    req=opener.open.call_args.args[0]; url=urlsplit(req.full_url)
    assert url.path=='/1471000/DrugPrdtPrmsnInfoService08/getDrugPrdtPrmsnDtlInq08'
    assert parse_qs(url.query)=={'serviceKey':['SYNTHETIC+a/b='],'pageNo':['1'],
        'numOfRows':['3'],'type':['xml'],'item_name':['타이레놀']}
    assert 'serviceKey=SYNTHETIC%2Ba%2Fb%3D' in url.query
    assert opener.open.call_count==1


def test_encoded_key_rejected_before_network(monkeypatch,capsys):
    monkeypatch.setenv('MFDS_API_KEY','SYNTHETIC%2BKEY')
    assert main(['--live'],transport=lambda *a:pytest.fail('must not call'))==1
    out=json.loads(capsys.readouterr().out)
    assert out['request_attempts']==0 and out['error']=='KEY_APPEARS_ENCODED_USE_DECODING_KEY'
    assert 'SYNTHETIC' not in str(out)


@pytest.mark.parametrize('body,code,message',[
    (b'<OpenAPI_ServiceResponse><cmmMsgHeader><returnReasonCode>30</returnReasonCode><returnAuthMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR</returnAuthMsg></cmmMsgHeader></OpenAPI_ServiceResponse>','30','SERVICE_KEY_IS_NOT_REGISTERED_ERROR'),
    (b'<response><header><resultCode>10</resultCode><resultMsg>INVALID_REQUEST_PARAMETER_ERROR</resultMsg></header></response>','10','INVALID_REQUEST_PARAMETER_ERROR'),
    (b'<response><header><resultCode>SYNTHETIC-SECRET</resultCode><resultMsg>https://example.invalid?serviceKey=SYNTHETIC-SECRET</resultMsg></header></response>','UNRECOGNIZED_REDACTED','UNRECOGNIZED_SERVER_MESSAGE_REDACTED'),
])
def test_http_error_body_allowlist_no_secret_url_or_retry(monkeypatch,capsys,body,code,message):
    from io import BytesIO
    import urllib.error
    monkeypatch.setenv('MFDS_API_KEY','SYNTHETIC-SECRET')
    calls=[]
    def fake(*a):
        calls.append(True)
        raise urllib.error.HTTPError('https://example.invalid?serviceKey=SYNTHETIC-SECRET',400,'private',{},BytesIO(body))
    assert main(['--live'],transport=fake)==1
    out=capsys.readouterr().out; result=json.loads(out)
    assert calls==[True] and result['http_status']==400
    assert result['api_error_code']==code and result['api_error_message']==message
    assert 'SYNTHETIC-SECRET' not in out and 'https://' not in out


@pytest.mark.parametrize('body,status',[
    (b'','UNAVAILABLE'), (b'SYNTHETIC-SECRET https://example.invalid','UNREADABLE_OR_NON_XML_REDACTED'),
    (b'x'*16385,'TOO_LARGE_REDACTED'),
    (b'<!DOCTYPE x><x/>','UNSUPPORTED_REDACTED')])
def test_unsupported_error_body_is_not_logged(body,status):
    from io import BytesIO
    import urllib.error
    from backend.services.mfds.probe import safe_http_error
    exc=urllib.error.HTTPError('redacted',400,'redacted',{},BytesIO(body))
    result=safe_http_error(exc)
    assert result['error_body_status']==status
    assert 'SYNTHETIC-SECRET' not in str(result)


def test_safe_network_stage_classification():
    import socket,ssl,urllib.error
    from backend.services.mfds.probe import transport_stage
    assert transport_stage(urllib.error.URLError(socket.gaierror(-2,'synthetic')))=='DNS_RESOLUTION'
    assert transport_stage(urllib.error.URLError(OSError('Tunnel connection failed: 403 Forbidden')))=='PROXY_CONNECTION'
    assert transport_stage(ssl.SSLCertVerificationError('synthetic'))=='TLS_CERTIFICATE_VERIFICATION'
    assert transport_stage(TimeoutError('synthetic'))=='TIMEOUT_STAGE_UNDETERMINED'
