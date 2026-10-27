import urllib.error
from pathlib import Path

from backend.services.mfds.real_client import RealMfdsClient

DEFAULT_CFG = Path(__file__).parents[1] / "api_config.yaml"
DRUG_PAYLOAD = {
    "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
    "body": {"items": [
        {"ITEM_SEQ": "000123456", "ITEM_NAME": "타이레놀정500밀리그램", "CHART": "흰색 정제",
         "MAIN_ITEM_INGR": "[M040702]아세트아미노펜"},
        {"ITEM_SEQ": "999", "ITEM_NAME": "다른약"},
    ]},
}
EMPTY = {"header": {"resultCode": "03", "resultMsg": "NODATA"}, "body": {"items": []}}


class FakeTransport:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def __call__(self, url, params, timeout):
        self.calls.append((url, dict(params), timeout))
        r = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(r, Exception):
            raise r
        return r


def client(*responses, **kw):
    t = FakeTransport(*responses)
    kw.setdefault("api_key", "TESTKEY")
    return RealMfdsClient(transport=t, sleep=lambda s: None, **kw), t


def test_find_by_code_is_skipped_until_insurance_code_spec_is_configured():
    # 기본 설정은 보험코드 조회 명세 미확인 → ITEM_SEQ 와 약품코드를 비교하지 않고 호출도 하지 않는다
    c, t = client(DRUG_PAYLOAD)
    assert c.find_by_code("000123456") == [] and t.calls == []
    assert not c.last_failed


def test_find_by_code_uses_insurance_code_field_only_and_keeps_leading_zero(tmp_path):
    import yaml
    cfg = yaml.safe_load(DEFAULT_CFG.read_text(encoding="utf-8"))
    cfg["sources"]["drug"]["insurance_code_param"] = "edi_code"
    cfg["sources"]["drug"]["fields"]["insurance_code"] = "EDI_CODE"
    cfg["sources"].pop("health_food")
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    payload = {"header": {"resultCode": "00"}, "body": {"items": [
        {"ITEM_SEQ": "000123456", "ITEM_NAME": "가정", "EDI_CODE": "999"},          # ITEM_SEQ 만 같은 항목 → 제외
        {"ITEM_SEQ": "111", "ITEM_NAME": "나정", "EDI_CODE": "000123456",
         "MAIN_ITEM_INGR": "[M040702]아세트아미노펜"},
    ]}}
    c, _ = client(payload, config_path=p)
    items = c.find_by_code("000123456")
    assert [i.official_id for i in items] == ["111"]
    assert items[0].insurance_code == "000123456"
    assert items[0].ingredients[0].name == "아세트아미노펜"
    assert items[0].ingredients[0].ingredient_id == "M040702"
    assert items[0].ingredients[0].amount is None  # 함량 정보 없으면 추측하지 않는다


def test_retry_then_success():
    c, t = client(TimeoutError("timed out"), TimeoutError("timed out"), DRUG_PAYLOAD)
    items = c.search_by_name("타이레놀")
    assert items and not c.last_failed
    assert c.calls >= 3


def test_all_retries_fail_records_warning_not_exception():
    c, t = client(TimeoutError("timed out"), retries=2)
    assert c.search_by_name("타이레놀") == []
    assert c.last_failed
    assert any("조회 실패" in w and "재시도 2회" in w for w in c.last_warnings)
    assert "TESTKEY" not in " ".join(c.last_warnings)  # 키가 경고에 새지 않는다


def test_http_4xx_not_retried_5xx_retried():
    e403 = urllib.error.HTTPError("u", 403, "Forbidden", {}, None)
    c, _ = client(e403, retries=3)
    c.search_by_name("x")
    assert c.last_failed and "HTTP 403" in c.last_warnings[0]
    calls_4xx = c.calls

    e500 = urllib.error.HTTPError("u", 500, "err", {}, None)
    c2, _ = client(e500, retries=3)
    c2.search_by_name("x")
    assert c2.calls > calls_4xx


def test_api_error_code_is_failure_without_retry():
    c, _ = client({"header": {"resultCode": "30", "resultMsg": "SERVICE KEY IS NOT REGISTERED"}}, retries=3)
    assert c.search_by_name("x") == [] and c.last_failed
    assert "resultCode=30" in c.last_warnings[0]


def test_nodata_is_not_a_failure():
    c, _ = client(EMPTY)
    assert c.search_by_name("없는약") == [] and not c.last_failed


def test_missing_api_key_warns_and_makes_no_call():
    c, t = client(DRUG_PAYLOAD, api_key="")
    assert c.search_by_name("x") == [] and c.last_failed
    assert t.calls == [] and "MFDS_API_KEY" in c.last_warnings[0]


def test_cache_avoids_second_call_and_failures_not_cached():
    c, t = client(DRUG_PAYLOAD)
    c.search_by_name("타이레놀")
    n = c.calls
    c.search_by_name("타이레놀")
    assert c.calls == n  # 캐시 적중

    c2, _ = client(TimeoutError("x"), DRUG_PAYLOAD, retries=0)
    assert c2.search_by_name("a") == [] and c2.last_failed
    assert c2.search_by_name("a") and not c2.last_failed  # 실패는 캐시하지 않아 재조회됨


def test_item_as_single_dict_and_wrapped_item():
    one = {"header": {"resultCode": "00"}, "body": {"items": {"item": {"ITEM_SEQ": "1", "ITEM_NAME": "가정"}}}}
    wrapped = {"header": {"resultCode": "00"}, "body": {"items": [{"item": {"ITEM_SEQ": "2", "ITEM_NAME": "나정"}}]}}
    assert [i.official_id for i in client(one)[0].search_by_name("a")] == ["1"]
    assert [i.official_id for i in client(wrapped)[0].search_by_name("a")] == ["2"]


def test_api_key_sent_as_param_only():
    c, t = client(DRUG_PAYLOAD)
    c.search_by_name("타이레놀")
    assert all(call[1]["serviceKey"] == "TESTKEY" for call in t.calls)


def test_transport_error_never_exposes_request_or_private_text(caplog):
    secret = 'SYNTHETIC-SECRET-MARKER'
    private = 'SYNTHETIC-HEALTH-MARKER'
    c, _ = client(RuntimeError(f'https://example.invalid?serviceKey={secret}&q={private}'), retries=1)
    assert c.search_by_name('가상제품') == []
    assert c.last_failed
    assert secret not in str(c.last_warnings) + caplog.text
    assert private not in str(c.last_warnings) + caplog.text


def test_api_header_error_never_exposes_arbitrary_code_or_message(caplog):
    secret = 'SYNTHETIC-SECRET-MARKER'
    c, _ = client({'header': {'resultCode': secret, 'resultMsg': secret}}, retries=1)
    assert c.search_by_name('가상제품') == []
    assert c.last_failed
    assert secret not in str(c.last_warnings) + caplog.text
