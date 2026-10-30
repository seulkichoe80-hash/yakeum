"""Opt-in single-drug XML lookup and conservative record verification; no fallback."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import os
import logging
import re
import unicodedata
import urllib.error

from fastapi import HTTPException
import yaml

from . import probe
from .client import MfdsClient
from .real_client import DEFAULT_CONFIG, parse_item
from .sample_mapping import parse_sample_xml


class NoLookup(MfdsClient):
    last_warnings=[]
    last_failed=False
    def find_by_code(self, code):return []
    def search_by_name(self, name, limit=50):return []


log=logging.getLogger(__name__)

LOOKUP_FAILURE_CATEGORIES=frozenset({'API_RESULT_NOT_SUCCESS','PAGINATION_MISMATCH','PAGINATION_INVALID','PAGE_ROW_COUNT_MISMATCH','PRODUCT_FIELDS_INVALID','DUPLICATE_PRODUCT_IDS'})
class LookupFailure(Exception):pass


class LiveLookup:
    """One request per processing operation, cache shared across both sides.

    No pagination, redirects, retries or insurance-code requests. Not the
    administrator's durable one-shot probe; never reads/resets its ledger.
    """
    def __init__(self,key,transport=None):
        self.key=key;self.transport=transport;self.calls=0;self.cache={}
        self.diagnostics={};self.cache_reuses=0;self.budget_skips=0

    def summary(self):
        return {'response_version':'MFDS_LOOKUP_DIAGNOSTICS_V1','mode':'MFDS_LIVE',
                'provider':'MFDS_DRUG','service_path':probe.ENDPOINT.split('/1471000/')[-1],
                'request_attempts':self.calls,'automatic_retries':0,'automatic_next_page_requests':0,
                'timeout_seconds':15,'page':1,'page_size':3,
                'cache_reuses':self.cache_reuses,'budget_skips':self.budget_skips,
                'queries':[deepcopy(d) for d in self.diagnostics.values()]}

    def error_category(self,name):
        return self.diagnostics.get(name,{}).get('category','UNCONFIRMED')

    def lookup(self,name):
        if name in self.cache:
            self.cache_reuses+=1
            return self.cache[name]
        result=('ERROR',[])
        if not name or len(name)>200:
            return result
        if self.calls>=1:
            self.budget_skips+=1
            return ('BUDGET_EXHAUSTED',[])
        self.calls+=1
        diagnostic={'query_index':self.calls-1,'request_attempts':1,'outcome':'ERROR'}
        phase='FETCH'
        try:
            response=(self.transport or probe.fetch_xml)(self.key,name,1,3)
            phase='XML_PARSE'
            payload=parse_sample_xml(response)
            diagnostic['xml_valid']=True
            body=payload['body'];rows=body['items'];header=payload['header']
            phase='API_RESULT'
            if header.get('resultCode')!='00':
                code=str(header.get('resultCode',''))
                message=header.get('resultMsg','')
                diagnostic['api_error_code']=code if re.fullmatch(r'[0-9]{2,3}',code) else 'UNRECOGNIZED_REDACTED'
                diagnostic['api_error_message']=message if message in probe.SAFE_MESSAGES else 'UNRECOGNIZED_SERVER_MESSAGE_REDACTED'
                raise LookupFailure('API_RESULT_NOT_SUCCESS')
            diagnostic['api_success']=True
            phase='PAGINATION'
            if body.get('pageNo')!='1' or body.get('numOfRows')!='3':raise LookupFailure('PAGINATION_MISMATCH')
            total=body.get('totalCount','')
            if not re.fullmatch(r'[0-9]+',total):raise LookupFailure('PAGINATION_INVALID')
            total=int(total)
            diagnostic.update(total_count=total,received_count=len(rows))
            if len(rows)!=min(total,3):raise LookupFailure('PAGE_ROW_COUNT_MISMATCH')
            phase='PRODUCT_MAPPING'
            cfg=yaml.safe_load(DEFAULT_CONFIG.read_text())['sources']['drug']
            items=[parse_item(row,cfg) for row in rows]
            if any(i is None for i in items):raise LookupFailure('PRODUCT_FIELDS_INVALID')
            if len({i.official_id for i in items})!=len(items):raise LookupFailure('DUPLICATE_PRODUCT_IDS')
            result=('INCOMPLETE_PAGE' if total!=len(rows) else 'COMPLETE',items)
            diagnostic.update(outcome=result[0],category='INCOMPLETE_PAGE' if total!=len(rows) else 'LOOKUP_COMPLETED',
                              all_candidates_received=total==len(rows))
        except urllib.error.HTTPError as exc:
            diagnostic.update(category='HTTP_FAILURE',http_status=exc.code,**probe.safe_http_error(exc))
        except LookupFailure as exc:
            diagnostic.update(category=str(exc) if str(exc) in LOOKUP_FAILURE_CATEGORIES else 'LOOKUP_VALIDATION_FAILED',failure_stage=phase)
        except Exception as exc:
            if phase=='FETCH':
                category=('RESPONSE_ENCODING_INVALID' if isinstance(exc,UnicodeDecodeError) else
                          'RESPONSE_TOO_LARGE' if isinstance(exc,probe.ProbeError) and str(exc)=='RESPONSE_TOO_LARGE' else
                          probe.transport_stage(exc))
            else:
                category={'XML_PARSE':'XML_INVALID','API_RESULT':'API_RESPONSE_INVALID',
                          'PAGINATION':'PAGINATION_INVALID','PRODUCT_MAPPING':'PRODUCT_MAPPING_FAILED'}[phase]
            diagnostic.update(category=category,failure_stage=phase)
            if phase=='XML_PARSE' and isinstance(response,str):
                diagnostic.update(probe.body_diagnostic(response))
        if result[0]=='ERROR':
            # Fixed enum/number fields only; never exception text or request values.
            log.warning('MFDS_MATCH_FAILURE category=%s phase=%s http_status=%s',
                        diagnostic['category'],diagnostic.get('failure_stage','UNCONFIRMED'),diagnostic.get('http_status','NONE'))
        self.diagnostics[name]=diagnostic
        self.cache[name]=result
        return result


def configured_lookup(mode):
    if mode=='LOCAL_MOCK':return None
    if mode!='MFDS_LIVE':raise HTTPException(422,'지원하지 않는 의약품 매칭 방식입니다.')
    if os.environ.get('YAKEUM_MFDS_MATCH_ENABLED')!='1':
        raise HTTPException(503,'실제 식약처 매칭은 서버에서 비활성화되어 있습니다. 가상 매칭으로 대체하지 않습니다.')
    key=os.environ.get('MFDS_API_KEY','').strip()
    if not key or re.search(r'%[0-9a-fA-F]{2}',key):
        raise HTTPException(503,'식약처 Decoding 인증키의 비공개 서버 설정이 필요합니다. 가상 매칭으로 대체하지 않습니다.')
    return LiveLookup(key)


def text(value):
    return re.sub(r'\s+','',unicodedata.normalize('NFKC',str(value or ''))).casefold()


def unit(value):
    # Exact same unit aliases only, no scale/equivalent/granule conversion.
    return {'mg':'mg','밀리그램':'mg'}.get(text(value))


def amount(value):
    try:
        if value is None or isinstance(value,bool):return None
        value=Decimal(str(value))
        return value if value.is_finite() and value>=0 else None
    except (ValueError,InvalidOperation):return None


def verify_result(base,lookup):
    result=deepcopy(base)
    record=result.get('record')
    if record is None or result['status']=='FAILED':return result
    result['warnings']=[w for w in result['warnings'] if w.get('message')!='공식 데이터에서 찾지 못함 (원본 값 보존)']
    record['mfds_product_id']=None
    for i in record['ingredients']:i['official_ingredient_id']=None
    result['match']={'source':None,'official_id':None,'match_method':None}
    result['status']='PARTIAL'
    def hold(message,status='PARTIAL'):
        result['status']=status
        result['warnings'].append({'code':'NORMALIZATION_FAILED','message':message,'field':None})
        return result
    kind,items=lookup.lookup(record['product_name_raw'])
    if kind!='COMPLETE':
        messages={'ERROR':'식약처 조회에 실패했습니다.', 'INCOMPLETE_PAGE':'전체 검색 후보를 받지 못했습니다.',
                  'BUDGET_EXHAUSTED':'이번 처리의 외부 조회 한도(1회)를 사용했습니다.'}
        return hold(messages[kind]+(' 오류 분류: '+lookup.error_category(record['product_name_raw'])+'.' if kind=='ERROR' else '')+' 원본을 보존하고 비교를 보류합니다.', 'UNMATCHED' if kind=='ERROR' else 'PARTIAL')
    if not items:return hold('식약처 검색 결과가 없어 제품을 확정하지 않습니다.','UNMATCHED')
    # Do not filter several returned candidates down to a unique match.
    if len(items)!=1:return hold('복수 식약처 후보가 있어 자동 선택하지 않고 비교를 보류합니다.')
    item=items[0]
    if text(item.name)!=text(record['product_name_raw']):
        return hold('제품명이 정확히 대응하지 않아 비교를 보류합니다. 함량 표기를 제거해 매칭하지 않습니다.')
    if record.get('drug_code') and item.insurance_code!=record['drug_code']:
        return hold('원본 보험코드와 공식 보험코드의 일치를 확인하지 못해 비교를 보류합니다.')
    if record.get('unit')!='정':
        return hold('공식 함량 기준(1정)과 원본 투약 단위를 대응하지 못해 비교를 보류합니다.')
    source=record['ingredients'];official=item.ingredients
    a=[text(i['ingredient_name_raw']) for i in source];b=[text(i.name) for i in official]
    if not a or not b or len(set(a))!=len(a) or len(set(b))!=len(b) or set(a)!=set(b):
        return hold('성분 구성이 정확히 대응하지 않아 비교를 보류합니다.')
    for ing in source:
        off=next(i for i in official if text(i.name)==text(ing['ingredient_name_raw']))
        if (amount(ing['product_strength']) is None or amount(off.amount) is None
                or not unit(ing['product_strength_unit']) or not unit(off.unit)
                or amount(ing['product_strength'])!=amount(off.amount)
                or unit(ing['product_strength_unit'])!=unit(off.unit)):
            return hold('성분 함량·단위가 미확인 또는 불일치하여 비교를 보류합니다. 환산하거나 원본을 덮어쓰지 않습니다.')
    for ing in source:
        ing['official_ingredient_id']=next(i.ingredient_id for i in official if text(i.name)==text(ing['ingredient_name_raw']))
    record['mfds_product_id']=item.official_id
    record['product_name_normalized']=item.name
    result['status']='MATCHED'
    result['match']={'source':'MFDS_DRUG','official_id':item.official_id,'match_method':'NAME_EXACT'}
    return result


def normalize_photo(extraction,lookup,*,expected_family_member_id):
    from backend.services.normalization.structured import normalize_structured_record
    return verify_result(normalize_structured_record(extraction,NoLookup(),
        expected_family_member_id=expected_family_member_id),lookup)
