"""Sanitized lookup diagnostics only; all HTTP errors and responses are fake."""
from io import BytesIO
import json
import socket
import ssl
import urllib.error

import pytest

from backend.services.mfds.live_matching import LiveLookup
from backend.tests.test_live_mfds_matching import xml


@pytest.mark.parametrize('error,category',[
    (urllib.error.URLError(socket.gaierror(-2,'SYNTHETIC-SECRET')),'DNS_RESOLUTION'),
    (urllib.error.URLError(OSError('Tunnel connection failed: 403 Forbidden SYNTHETIC-SECRET')),'PROXY_CONNECTION'),
    (ssl.SSLCertVerificationError('SYNTHETIC-SECRET'),'TLS_CERTIFICATE_VERIFICATION'),
    (TimeoutError('SYNTHETIC-SECRET'),'TIMEOUT_STAGE_UNDETERMINED'),
    (RuntimeError('SYNTHETIC-SECRET https://private.invalid'),'UNCLASSIFIED_LOCAL_OR_TRANSPORT'),
])
def test_transport_errors_classified_without_echo(error,category,caplog):
    calls=[]
    def fake(*args):calls.append(True);raise error
    lookup=LiveLookup('SYNTHETIC-SECRET',transport=fake)
    assert lookup.lookup('SYNTHETIC-QUERY')[0]=='ERROR'
    assert lookup.lookup('SYNTHETIC-QUERY')[0]=='ERROR'
    result=lookup.summary();assert result['queries'][0]['category']==category
    assert result['request_attempts']==1 and result['cache_reuses']==1 and calls==[True]
    output=json.dumps(result)+caplog.text
    assert 'SYNTHETIC-SECRET' not in output and 'SYNTHETIC-QUERY' not in output and 'https://' not in output


def test_http503_same_safe_diagnostics_as_admin_no_retry(caplog):
    def fake(*args):
        raise urllib.error.HTTPError('https://private.invalid?serviceKey=SYNTHETIC-SECRET',503,'private',
            {'Content-Type':'text/plain','Server':'envoy','Via':'SYNTHETIC-SECRET', 'Set-Cookie':'SYNTHETIC-SECRET'},
            BytesIO(b'upstream connect error SYNTHETIC-SECRET https://private.invalid'))
    lookup=LiveLookup('SYNTHETIC-SECRET',transport=fake)
    assert lookup.lookup('SYNTHETIC-QUERY')[0]=='ERROR'
    result=lookup.summary();query=result['queries'][0]
    assert query['http_status']==503 and query['category']=='HTTP_FAILURE'
    assert query['diagnostic_headers']['content_type']=='text/plain' and query['diagnostic_headers']['server']=='envoy'
    assert query['body_signals']==['UPSTREAM_CONNECT_ERROR_TEXT'] and query['origin_attribution']=='UNCONFIRMED'
    assert 'category=HTTP_FAILURE' in caplog.text and 'http_status=503' in caplog.text
    assert 'SYNTHETIC-SECRET' not in json.dumps(result)+caplog.text
    assert 'https://' not in json.dumps(result)+caplog.text


@pytest.mark.parametrize('response,category',[
    ('<broken','XML_INVALID'),
    (xml().replace('<resultCode>00','<resultCode>30'),'API_RESULT_NOT_SUCCESS'),
    (xml().replace('<pageNo>1','<pageNo>2'),'PAGINATION_MISMATCH'),
    (xml().replace('<totalCount>1','<totalCount>bad'),'PAGINATION_INVALID'),
    (xml().replace('<ITEM_SEQ>','<OTHER_ID>').replace('</ITEM_SEQ>','</OTHER_ID>'),'PRODUCT_FIELDS_INVALID'),
])
def test_parse_and_validation_failures_distinct(response,category):
    lookup=LiveLookup('SYNTHETIC-SECRET',transport=lambda *a:response)
    assert lookup.lookup('query')[0]=='ERROR'
    assert lookup.summary()['queries'][0]['category']==category


def test_partial_response_counts_source_and_budget_preserved():
    lookup=LiveLookup('SYNTHETIC-SECRET',transport=lambda *a:xml('partial'))
    assert lookup.lookup('one')[0]=='INCOMPLETE_PAGE'
    assert lookup.lookup('two')[0]=='BUDGET_EXHAUSTED'
    result=lookup.summary();q=result['queries'][0]
    assert q['category']=='INCOMPLETE_PAGE' and q['total_count']==7 and q['received_count']==3
    assert result['mode']=='MFDS_LIVE' and result['provider']=='MFDS_DRUG'
    assert result['request_attempts']==1 and result['budget_skips']==1


def test_http200_non_xml_retains_only_safe_body_signals():
    response='service unavailable SYNTHETIC-SECRET https://private.invalid'
    lookup=LiveLookup('SYNTHETIC-SECRET',transport=lambda *a:response)
    assert lookup.lookup('query')[0]=='ERROR'
    query=lookup.summary()['queries'][0]
    assert query['category']=='XML_INVALID' and query['body_format_hint']=='TEXT'
    assert query['body_signals']==['SERVICE_UNAVAILABLE_TEXT']
    assert 'SYNTHETIC-SECRET' not in json.dumps(query) and 'https://' not in json.dumps(query)
