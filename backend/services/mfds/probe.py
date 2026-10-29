"""Opt-in, one-request MFDS XML probe. Default is configuration check only."""
import argparse
import json
import os
import re
import socket
import xml.etree.ElementTree as ET
from pathlib import Path
import ssl
import urllib.error
import urllib.parse
import urllib.request

import yaml

from .real_client import DEFAULT_CONFIG, parse_item
from .sample_mapping import parse_sample_xml

ENDPOINT = 'https://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService08/getDrugPrdtPrmsnDtlInq08'
MAX_BYTES = 2_000_000


class ProbeError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward a keyed URL to another destination.


def fetch_xml(key, name, page, rows):
    # urllib does not retry; this opener refuses redirects and retains the
    # environment's proxy routing. Trust the configured CA, never disable TLS.
    ca_file = os.environ.get('SSL_CERT_FILE') or os.environ.get('REQUESTS_CA_BUNDLE')
    context = ssl.create_default_context(cafile=ca_file)
    opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=context))
    query = urllib.parse.urlencode({'serviceKey': key, 'item_name': name,
                                   'pageNo': page, 'numOfRows': rows, 'type': 'xml'})
    request = urllib.request.Request(ENDPOINT+'?'+query, headers={'Accept': 'application/xml'})
    with opener.open(request, timeout=15) as response:
        raw = response.read(MAX_BYTES+1)
    if len(raw) > MAX_BYTES:
        raise ProbeError('RESPONSE_TOO_LARGE')
    return raw.decode('utf-8-sig')


def inspect_xml(text, page=1, rows=3):
    try:
        payload = parse_sample_xml(text)
        header, body = payload['header'], payload['body']
        if header.get('resultCode') != '00':
            # No arbitrary server message/code in logs. No-data codes require
            # official confirmation; successful empty result uses 00 + total=0.
            raise ProbeError('API_RESULT_NOT_SUCCESS')
        def integer(field):
            value = body.get(field, '')
            if not value.isascii() or not value.isdigit():
                raise ProbeError('PAGINATION_INVALID')
            return int(value)
        total, actual_page, actual_rows = (integer(f) for f in ('totalCount', 'pageNo', 'numOfRows'))
        if actual_page != page or actual_rows != rows or page < 1 or rows < 1:
            raise ProbeError('PAGINATION_MISMATCH')
        expected = min(rows, max(0, total-(page-1)*rows))
        items = body['items']
        if len(items) != expected:
            raise ProbeError('PAGE_ROW_COUNT_MISMATCH')
        cfg = yaml.safe_load(DEFAULT_CONFIG.read_text())['sources']['drug']
        mapped = [parse_item(item, cfg) for item in items]
        if any(item is None for item in mapped):
            raise ProbeError('PRODUCT_FIELDS_INVALID')
        ids = [item.official_id for item in mapped]
        if len(ids) != len(set(ids)):
            raise ProbeError('DUPLICATE_PRODUCT_IDS')
        complete = page == 1 and len(items) == total
        return {'xml_valid': True, 'api_success': True, 'page': page, 'page_size': rows,
                'total_count': total, 'received_count': len(items), 'page_valid': True,
                'all_candidates_received': complete,
                'next_page_available': page*rows < total,
                'automatic_next_page_requests': 0,
                'unique_candidate_evidence': complete and total == 1,
                'ingredient_strength_verified_against_user_record': False,
                'products': [{'id_present': bool(item.official_id), 'name_present': bool(item.name),
                              'main_ingredients_present': bool(raw.get('MAIN_ITEM_INGR')),
                              'material_present': bool(raw.get('MATERIAL_NAME')),
                              'insurance_code_known': item.insurance_code is not None,
                              'ingredient_count': len(item.ingredients),
                              'direct_amount_count': sum(i.amount is not None for i in item.ingredients),
                              'unknown_amount_count': sum(i.amount is None for i in item.ingredients)}
                             for raw, item in zip(items, mapped)]}
    except ProbeError:
        raise
    except Exception:
        raise ProbeError('XML_OR_MAPPING_INVALID') from None



# Only recognized fixed server messages may leave memory. Arbitrary text can
# echo credentials, URLs or user data, so redaction by regex alone is insufficient.
SAFE_MESSAGES = frozenset({
    'SERVICE_KEY_IS_NOT_REGISTERED_ERROR', 'SERVICE_KEY_IS_NOT_REGISTERED',
    'INVALID_REQUEST_PARAMETER_ERROR', 'SERVICE_ACCESS_DENIED_ERROR',
    'NO_MANDATORY_REQUEST_PARAMETERS_ERROR', 'HTTP_ERROR',
    'LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR',
    'SERVICE_KEY_IS_NOT_REGISTERED_ERROR.', 'HTTP ROUTING ERROR',
})



def safe_diagnostic_headers(headers):
    """Return allowlisted enums, bounded numbers and presence flags only."""
    headers = headers or {}
    def value(name):
        return str(headers.get(name, '') or '')
    media = value('Content-Type').split(';', 1)[0].strip().lower()
    allowed_media = {'application/xml', 'text/xml', 'application/json',
                     'text/html', 'text/plain', 'application/problem+json'}
    result = {'content_type': media if media in allowed_media else 'OTHER_REDACTED' if media else 'UNAVAILABLE',
              'via_present': bool(value('Via')),
              'request_id_present': any(value(k) for k in ('X-Request-ID', 'X-Correlation-ID', 'CF-Ray'))}
    server = value('Server').lower().strip()
    known_servers = {'nginx', 'envoy', 'cloudflare', 'squid', 'apache', 'istio-envoy'}
    result['server'] = server if server in known_servers else 'OTHER_REDACTED' if server else 'UNAVAILABLE'
    retry = value('Retry-After')
    result['retry_after_present'] = bool(retry)
    if re.fullmatch(r'[0-9]{1,5}', retry) and int(retry) <= 86400:
        result['retry_after_seconds'] = int(retry)
    cache = value('X-Cache').strip().upper()
    if cache in {'HIT', 'MISS', 'BYPASS', 'ERROR'}:
        result['cache_status'] = cache
    proxy = value('Proxy-Status').lower()
    result['proxy_status_present'] = bool(proxy)
    # RFC proxy errors: emit only fixed category names, never proxy identities.
    for error in ('dns_error', 'connection_timeout', 'connection_refused',
                  'destination_unavailable', 'tls_protocol_error', 'tls_certificate_error'):
        if re.search(r'(?:^|[; ,])error="?' + error + r'"?(?:$|[; ,])', proxy):
            result['proxy_error_category'] = error
            break
    squid = value('X-Squid-Error').split(' ', 1)[0]
    if squid in {'ERR_CONNECT_FAIL', 'ERR_DNS_FAIL', 'ERR_ACCESS_DENIED', 'ERR_SECURE_CONNECT_FAIL', 'ERR_READ_TIMEOUT'}:
        result['squid_error_category'] = squid
    return result


def body_diagnostic(text):
    """Keep useful non-XML categories without copying server text."""
    stripped = text.lstrip().lower()
    signals = []
    for phrase, signal in (
        ('upstream connect error', 'UPSTREAM_CONNECT_ERROR_TEXT'),
        ('no healthy upstream', 'NO_HEALTHY_UPSTREAM_TEXT'),
        ('service unavailable', 'SERVICE_UNAVAILABLE_TEXT'),
        ('gateway timeout', 'GATEWAY_TIMEOUT_TEXT'),
        ('access denied', 'ACCESS_DENIED_TEXT')):
        if phrase in stripped:
            signals.append(signal)
    fmt = ('HTML' if stripped.startswith(('<!doctype html', '<html')) else
           'JSON_LIKE' if stripped.startswith(('{', '[')) else
           'XML_LIKE' if stripped.startswith('<') else 'TEXT')
    return {'body_format_hint': fmt, 'body_signals': signals}


def safe_http_error(exc):
    result = {'failure_stage': 'HTTP_RESPONSE',
              'diagnostic_headers': safe_diagnostic_headers(getattr(exc, 'headers', None)),
              'origin_attribution': 'UNCONFIRMED'}
    try:
        raw = exc.read(16_385)
        result['error_body_bytes_read'] = len(raw)
        if not raw:
            return {**result, 'error_body_status': 'UNAVAILABLE'}
        if len(raw) > 16_384:
            return {**result, 'error_body_status': 'TOO_LARGE_REDACTED'}
        text = raw.decode('utf-8-sig')
        result.update(body_diagnostic(text))
        if result['body_format_hint'] == 'JSON_LIKE':
            try:
                obj = json.loads(text)
                if isinstance(obj, dict):
                    code = str(obj.get('code', obj.get('errorCode', ''))).strip()
                    message = obj.get('message', obj.get('error', ''))
                    result['api_error_code'] = code if re.fullmatch(r'[0-9]{2,3}', code) else 'UNRECOGNIZED_REDACTED'
                    result['api_error_message'] = message if isinstance(message, str) and message in SAFE_MESSAGES else 'UNRECOGNIZED_SERVER_MESSAGE_REDACTED'
                    return {**result, 'error_body_status': 'JSON_PARSED'}
            except (ValueError, TypeError):
                pass
        if re.search(r'<!\s*(?:DOCTYPE|ENTITY)\b', text, re.I):
            return {**result, 'error_body_status': 'UNSUPPORTED_REDACTED'}
        root = ET.fromstring(text)
        # Portal gateway and normal API error envelopes; never print the tree.
        code = next((root.findtext(path) for path in (
            './cmmMsgHeader/returnReasonCode', './header/resultCode',
            './response/header/resultCode') if root.findtext(path)), '')
        message = next((root.findtext(path) for path in (
            './cmmMsgHeader/returnAuthMsg', './header/resultMsg',
            './response/header/resultMsg', './cmmMsgHeader/errMsg') if root.findtext(path)), '')
        code, message = code.strip(), message.strip()
        result['error_body_status'] = 'XML_PARSED'
        result['api_error_code'] = code if re.fullmatch(r'[0-9]{2,3}', code) else 'UNRECOGNIZED_REDACTED'
        result['api_error_message'] = message if message in SAFE_MESSAGES else 'UNRECOGNIZED_SERVER_MESSAGE_REDACTED'
        return result
    except Exception:
        return {**result, 'error_body_status': 'UNREADABLE_OR_NON_XML_REDACTED'}
    finally:
        try:
            exc.close()
        except Exception:
            pass


def transport_stage(exc):
    reason = getattr(exc, 'reason', exc)
    if isinstance(reason, ssl.SSLCertVerificationError):
        return 'TLS_CERTIFICATE_VERIFICATION'
    if isinstance(reason, ssl.SSLError):
        return 'TLS_NEGOTIATION'
    if isinstance(reason, socket.gaierror):
        return 'DNS_RESOLUTION'
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return 'TIMEOUT_STAGE_UNDETERMINED'
    text = str(reason).lower()  # Memory only; never output exception text.
    if 'tunnel connection failed' in text or 'proxy' in text:
        return 'PROXY_CONNECTION'
    return 'UNCLASSIFIED_LOCAL_OR_TRANSPORT'


def main(argv=None, *, transport=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--live', action='store_true', help='Explicitly authorize ONE request; no retry/pagination')
    modes.add_argument('--xml', type=Path, help='Offline XML file; no request')
    parser.add_argument('--name', default='타이레놀', help='Public product search term only, never personal data')
    parser.add_argument('--page', type=int, default=1)
    parser.add_argument('--rows', type=int, default=3)
    args = parser.parse_args(argv)
    result = {'mode': 'live' if args.live else 'offline' if args.xml else 'configuration_only',
              'request_attempts': 0, 'automatic_retries': 0}
    try:
        if not 1 <= args.page <= 10000 or not 1 <= args.rows <= 100:
            raise ProbeError('INVALID_PAGE_ARGUMENTS')
        cfg = yaml.safe_load(DEFAULT_CONFIG.read_text())['sources']['drug']
        key = os.environ.get('MFDS_API_KEY', '').strip()
        result['key_registered'] = bool(key)  # Does not establish validity or approval.
        if args.xml:
            if args.xml.stat().st_size > MAX_BYTES:
                raise ProbeError('RESPONSE_TOO_LARGE')
            text = args.xml.read_text(encoding='utf-8-sig')
        elif args.live:
            if not key:
                raise ProbeError('KEY_MISSING')
            if re.search(r'%[0-9a-fA-F]{2}', key):
                raise ProbeError('KEY_APPEARS_ENCODED_USE_DECODING_KEY')
            if not args.name.strip() or len(args.name) > 100:
                raise ProbeError('INVALID_PRODUCT_QUERY')
            result['request_attempts'] = 1  # Attempt, not proof of server receipt.
            text = (transport or fetch_xml)(key, args.name, args.page, args.rows)
        else:
            print(json.dumps(result, ensure_ascii=False))
            return 0
        result.update(inspect_xml(text, args.page, args.rows))
    except ProbeError as exc:
        result['error'] = str(exc)
    except urllib.error.HTTPError as exc:
        result['error'] = 'HTTP_FAILURE'
        result['http_status'] = exc.code
        result.update(safe_http_error(exc))
    except Exception as exc:
        # Never print exceptions, URLs, response text, names or credential values.
        result['error'] = 'TRANSPORT_OR_FILE_FAILURE'
        result['failure_stage'] = transport_stage(exc)
    print(json.dumps(result, ensure_ascii=False))
    return 1 if 'error' in result else 0


if __name__ == '__main__':
    raise SystemExit(main())
