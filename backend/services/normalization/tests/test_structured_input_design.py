"""A(AI 추출) → B(정규화) 입력 경계 설계 검증 테스트.

주의 (설계 단계):
- `normalize_structured_record` 는 설계 검증용 **프로토타입**이며 이 테스트 파일 안에만 있다.
  B 모듈로 승격하거나 팀장 통합본과 연결하지 않는다 (통합 코드는 팀장 승인·조율 후).
- A 코드는 병합하지 않았다. `a_result()` 는 `codex/a-extraction-contract` 의 adapter.py 출력 형태
  (ExtractionResult + 공통 MedicationRecord)를 읽기 전용으로 확인해 흉내 낸 **가상 데이터**다.
- MockMfdsClient 만 사용한다. 실제 식약처 API·HIRA 파일·API Key·건강정보는 쓰지 않는다.
- 아래 시나리오 번호(S1~S14)는 DESIGN_A_TO_B.md 의 표와 같다.
"""
import copy
from typing import Any, Dict, List, Optional

import pytest

from backend.services.mfds.mock_client import MockMfdsClient
from backend.services.mfds.models import OfficialIngredient, OfficialItem
from backend.services.normalization.adapter import RECORD_KEYS, to_error_detail, validate_common_result
from backend.services.normalization.matcher import match
from backend.services.normalization.name_normalizer import normalize_name

FAMILY = "00000000-0000-4000-8000-000000000001"
OTHER_FAMILY = "00000000-0000-4000-8000-000000000002"
A_STATUSES = ("SUCCESS", "NEEDS_CONFIRMATION", "FAILED")
THRESHOLD = 0.9


# ----------------------------------------------------------------------------- 프로토타입
def _detail(code: str, message: str, field: Optional[str] = None) -> Dict[str, Optional[str]]:
    return {"code": code, "message": message, "field": field}


def _failed(warnings, errors) -> Dict[str, Any]:
    return {"status": "FAILED", "record": None,
            "match": {"source": None, "official_id": None, "match_method": None},
            "warnings": warnings, "errors": errors}


def normalize_structured_record(extraction_result: Dict[str, Any], client, *,
                                expected_family_member_id: str, threshold: float = THRESHOLD) -> Dict[str, Any]:
    """A 의 ExtractionResult 1건 → 공통 NormalizationResult(Contract B) 1건.

    - 입력은 변경하지 않는다. user_confirmed / confidence / record_id / source_record_id / record_date /
      source_type / 원본 제품명·성분·수량 문자열은 그대로 둔다 (B 는 사용자 확인을 대신하지 않는다).
    - B 가 채우는 것: product_name_normalized, mfds_product_id(단일 매칭만), 빈 성분의 공식 성분,
      ingredient_name_normalized(규칙 정규화). 공식 성분 ID·함량을 추측하지 않는다.
    """
    if not isinstance(extraction_result, dict) or extraction_result.get("status") not in A_STATUSES:
        return _failed([], [_detail("NORMALIZATION_FAILED", "지원하지 않는 추출 결과 형식입니다.")])
    a_warnings = [dict(w) for w in extraction_result.get("warnings") or []]
    a_errors = [dict(e) for e in extraction_result.get("errors") or []]

    if extraction_result["status"] == "FAILED":
        return _failed(a_warnings, a_errors or [_detail("AI_EXTRACTION_FAILED", "AI 추출에 실패했습니다.")])
    src = extraction_result.get("record")
    if not isinstance(src, dict):  # NEEDS_CONFIRMATION 이지만 record 가 없음 → 정규화할 대상이 없다
        return _failed([], a_warnings + a_errors or [_detail("REQUIRED_FIELD_MISSING", "정규화할 기록이 없습니다.")])

    if src.get("family_member_id") != expected_family_member_id:
        return _failed(a_warnings, [_detail("REQUIRED_FIELD_MISSING", "기록의 가족 구성원이 요청과 일치하지 않습니다.", "family_member_id")])
    name_raw = src.get("product_name_raw")
    if not isinstance(name_raw, str) or not name_raw.strip():
        return _failed(a_warnings, [_detail("REQUIRED_FIELD_MISSING", "제품명을 확인할 수 없습니다.", "product_name_raw")])

    record = copy.deepcopy(src)
    warnings: List[Dict[str, Optional[str]]] = a_warnings
    status, info = "UNMATCHED", {"source": None, "official_id": None, "match_method": None}
    candidates: List[OfficialItem] = []
    try:
        out = match(client, None, name_raw.strip(), threshold)  # A 는 약품코드가 없다 → 이름 매칭만
        warnings += [to_error_detail(w) for w in out.warnings]
        candidates = out.candidates
        method = out.method
    except Exception as e:  # noqa: BLE001
        warnings.append(to_error_detail(f"공식 데이터 조회 실패: {type(e).__name__}"))
        method = "NONE"

    record["product_name_normalized"] = normalize_name(name_raw)
    for ing in record.get("ingredients") or []:
        if isinstance(ing, dict) and ing.get("ingredient_name_raw"):
            ing["ingredient_name_normalized"] = normalize_name(ing["ingredient_name_raw"])

    if not candidates:
        warnings.append(to_error_detail("공식 데이터에서 찾지 못함 (원본 값 보존)"))
    elif len(candidates) > 1:
        status = "PARTIAL"
        info["match_method"] = method
        warnings.append(to_error_detail(f"후보 {len(candidates)}건 ({method}): " + ", ".join(c.official_id for c in candidates)))
    else:
        item = candidates[0]
        status = "MATCHED"
        info = {"source": item.source, "official_id": item.official_id, "match_method": method}
        record["mfds_product_id"] = item.official_id
        record["product_name_normalized"] = item.name
        if not record.get("ingredients"):
            if item.ingredients:
                record["ingredients"] = [{
                    "ingredient_name_raw": None,  # 원본에서 확인한 값이 아님
                    "ingredient_name_normalized": i.name,
                    "product_strength": None if i.amount is None else format(i.amount.normalize(), "f"),
                    "product_strength_unit": i.unit,
                    "official_ingredient_id": i.ingredient_id,
                } for i in item.ingredients]
            else:
                status = "PARTIAL"
                warnings.append(to_error_detail("공식 데이터에 성분 정보가 없어 일부만 확인됨"))
    return {"status": status, "record": record, "match": info, "warnings": warnings, "errors": []}


# ----------------------------------------------------------------------------- 가상 입력 (A 출력 형태)
def a_record(**over) -> Dict[str, Any]:
    rec = {
        "record_id": "10000000-0000-4000-8000-000000000001",
        "family_member_id": FAMILY,
        "source_type": "MEDICINE_BAG",
        "source_record_id": "virtual-image-001:1",
        "record_date": "2026-10-14",
        "dispensing_date": None, "prescribing_institution": None, "dispensing_institution": None,
        "product_name_raw": "타이레놀정500밀리그램",
        "product_name_normalized": None, "drug_code": None, "drug_category": None,
        "unit": "정", "dose_per_administration": "1", "administrations_per_day": "2", "duration_days": "7",
        "dosage_text_raw": "하루 두 번 한 정",
        "mfds_product_id": None,
        "ingredients": [{"ingredient_name_raw": "아세트아미노펜", "ingredient_name_normalized": None,
                         "product_strength": "500", "product_strength_unit": "mg", "official_ingredient_id": None}],
        "confidence": "0.91", "user_confirmed": False,
    }
    rec.update(over)
    return rec


def a_result(status="SUCCESS", record="default", warnings=None, errors=None, **record_over) -> Dict[str, Any]:
    return {"status": status, "record": a_record(**record_over) if record == "default" else record,
            "warnings": warnings or [], "errors": errors or []}


class CountingClient(MockMfdsClient):
    calls = 0

    def search_by_name(self, name, limit=50):
        CountingClient.calls += 1
        return super().search_by_name(name, limit)


TYLE = OfficialItem("MFDS_DRUG", "OFF-1", "타이레놀정500밀리그램",
                    [OfficialIngredient("아세트아미노펜", None, None, "M040702")], None, None)
GANARIL_A = OfficialItem("MFDS_DRUG", "OFF-2", "가나릴캡슐", [OfficialIngredient("가짜성분A")])
GANARIL_B = OfficialItem("MFDS_DRUG", "OFF-3", "가나릴정", [OfficialIngredient("가짜성분B")])
NO_INGR = OfficialItem("MFDS_HEALTH_FOOD", "OFF-4", "비타민건기식", [])


def run(result, items, family=FAMILY):
    return normalize_structured_record(result, MockMfdsClient(items=items), expected_family_member_id=family)


def check_contract(out):
    assert validate_common_result(out) == [], out


# ----------------------------------------------------------------------------- 시나리오
def test_s1_matched_keeps_raw_and_does_not_confirm_user():
    out = run(a_result(), [TYLE])
    check_contract(out)
    rec = out["record"]
    assert out["status"] == "MATCHED"
    assert out["match"] == {"source": "MFDS_DRUG", "official_id": "OFF-1", "match_method": "NAME_EXACT"}
    assert rec["mfds_product_id"] == "OFF-1" and rec["product_name_normalized"] == "타이레놀정500밀리그램"
    assert rec["product_name_raw"] == "타이레놀정500밀리그램"
    assert rec["user_confirmed"] is False and rec["confidence"] == "0.91"


def test_s2_unmatched_preserves_record():
    out = run(a_result(product_name_raw="없는약정"), [TYLE])
    check_contract(out)
    assert out["status"] == "UNMATCHED"
    assert out["match"] == {"source": None, "official_id": None, "match_method": None}
    assert out["record"]["product_name_raw"] == "없는약정" and out["record"]["mfds_product_id"] is None
    assert any(w["code"] == "OFFICIAL_MATCH_NOT_FOUND" for w in out["warnings"])


def test_s3_multiple_candidates_are_partial_and_not_confirmed():
    out = run(a_result(product_name_raw="가나릴"), [GANARIL_A, GANARIL_B])
    check_contract(out)
    assert out["status"] == "PARTIAL"
    assert out["match"]["official_id"] is None and out["record"]["mfds_product_id"] is None
    assert any("후보 2건" in w["message"] for w in out["warnings"])


def test_s4_missing_ingredients_filled_from_official_without_claiming_raw():
    out = run(a_result(ingredients=[]), [TYLE])
    check_contract(out)
    assert out["status"] == "MATCHED"
    ing = out["record"]["ingredients"][0]
    assert ing["ingredient_name_raw"] is None and ing["ingredient_name_normalized"] == "아세트아미노펜"
    assert ing["product_strength"] is None and ing["official_ingredient_id"] == "M040702"  # 함량은 추측하지 않음


def test_s5_missing_ingredients_and_no_official_ingredients_is_partial():
    out = run(a_result(product_name_raw="비타민건기식", ingredients=[]), [NO_INGR])
    check_contract(out)
    assert out["status"] == "PARTIAL" and out["record"]["ingredients"] == []
    assert out["match"]["official_id"] == "OFF-4"  # 단일 매칭은 유지, 성분만 미확인


def test_s6_missing_product_name_fails_without_lookup():
    CountingClient.calls = 0
    out = normalize_structured_record(a_result(product_name_raw=None), CountingClient(items=[TYLE]),
                                      expected_family_member_id=FAMILY)
    check_contract(out)
    assert out["status"] == "FAILED" and out["record"] is None and CountingClient.calls == 0
    assert out["errors"][0]["code"] == "REQUIRED_FIELD_MISSING" and out["errors"][0]["field"] == "product_name_raw"


def test_s7_multiple_ingredients_keep_order_strength_and_unit():
    ings = [
        {"ingredient_name_raw": "성분가", "ingredient_name_normalized": None, "product_strength": "0.50",
         "product_strength_unit": "mg", "official_ingredient_id": None},
        {"ingredient_name_raw": "성분나", "ingredient_name_normalized": None, "product_strength": None,
         "product_strength_unit": None, "official_ingredient_id": None},
        {"ingredient_name_raw": "성분다", "ingredient_name_normalized": None, "product_strength": "0",
         "product_strength_unit": "mcg", "official_ingredient_id": None},
    ]
    out = run(a_result(ingredients=ings), [TYLE])
    check_contract(out)
    got = out["record"]["ingredients"]
    assert [i["ingredient_name_raw"] for i in got] == ["성분가", "성분나", "성분다"]
    assert [i["product_strength"] for i in got] == ["0.50", None, "0"]  # 문자열·null·0 구분 그대로
    assert [i["product_strength_unit"] for i in got] == ["mg", None, "mcg"]
    assert all(i["official_ingredient_id"] is None for i in got)  # 성분 동일성 확정 금지


def test_s8_family_mismatch_fails_without_lookup():
    CountingClient.calls = 0
    out = normalize_structured_record(a_result(family_member_id=OTHER_FAMILY), CountingClient(items=[TYLE]),
                                      expected_family_member_id=FAMILY)
    check_contract(out)
    assert out["status"] == "FAILED" and out["record"] is None and CountingClient.calls == 0
    assert out["errors"][0]["field"] == "family_member_id"


def test_s9_user_confirmed_is_never_raised_by_b():
    for status in ("SUCCESS", "NEEDS_CONFIRMATION"):
        out = run(a_result(status, warnings=[_detail("REQUIRED_FIELD_MISSING", "AI 신뢰도를 확인할 수 없습니다.", "confidence")]
                           if status == "NEEDS_CONFIRMATION" else None, confidence=None), [TYLE])
        assert out["record"]["user_confirmed"] is False  # MATCHED 여도 사용자 확인으로 바뀌지 않는다
        assert out["record"]["confidence"] is None
    # 이미 사용자가 확인한 값(true)은 그대로 둔다 (B 가 내리거나 올리지 않음)
    assert run(a_result(user_confirmed=True), [TYLE])["record"]["user_confirmed"] is True


def test_s10_a_failed_passes_through_without_lookup():
    CountingClient.calls = 0
    a = a_result("FAILED", record=None, errors=[_detail("AI_EXTRACTION_FAILED", "AI 인식 요청을 완료하지 못했습니다.")])
    out = normalize_structured_record(a, CountingClient(items=[TYLE]), expected_family_member_id=FAMILY)
    check_contract(out)
    assert out["status"] == "FAILED" and out["record"] is None and CountingClient.calls == 0
    assert out["errors"][0]["code"] == "AI_EXTRACTION_FAILED"


def test_s11_a_needs_confirmation_without_record_is_failed_with_reason_kept():
    a = a_result("NEEDS_CONFIRMATION", record=None,
                 warnings=[_detail("REQUIRED_FIELD_MISSING", "제품명을 확인할 수 없습니다.", "product_name_raw")])
    out = run(a, [TYLE])
    check_contract(out)
    assert out["status"] == "FAILED" and out["record"] is None
    assert out["errors"] == [_detail("REQUIRED_FIELD_MISSING", "제품명을 확인할 수 없습니다.", "product_name_raw")]


def test_s12_preserved_fields_and_input_not_mutated():
    a = a_result(dose_per_administration="0.5", duration_days=None, dosage_text_raw="아침 식후")
    before = copy.deepcopy(a)
    out = run(a, [TYLE])
    assert a == before  # 입력 불변
    rec = out["record"]
    for k in ("record_id", "family_member_id", "source_type", "source_record_id", "record_date", "unit",
              "dose_per_administration", "administrations_per_day", "duration_days", "dosage_text_raw",
              "confidence", "user_confirmed", "product_name_raw"):
        assert rec[k] == before["record"][k], k
    assert rec["duration_days"] is None  # null 유지
    assert [k for k in rec] == RECORD_KEYS
    assert rec["ingredients"][0]["product_strength"] == "500" and rec["ingredients"][0]["product_strength_unit"] == "mg"


def test_s13_lookup_failure_is_unmatched_with_warning_and_record_kept():
    class Boom(MockMfdsClient):
        def search_by_name(self, name, limit=50):
            raise RuntimeError("SECRET-VALUE")

    out = normalize_structured_record(a_result(), Boom(items=[]), expected_family_member_id=FAMILY)
    check_contract(out)
    assert out["status"] == "UNMATCHED" and out["record"]["product_name_raw"] == "타이레놀정500밀리그램"
    assert "SECRET-VALUE" not in str(out)  # 예외 원문은 노출하지 않는다


def test_s14_a_warnings_are_carried_with_b_warnings():
    a = a_result("NEEDS_CONFIRMATION", warnings=[_detail("REQUIRED_FIELD_MISSING", "AI 신뢰도를 확인할 수 없습니다.", "confidence")],
                 confidence=None, product_name_raw="없는약정")
    out = run(a, [TYLE])
    codes = [(w["code"], w["field"]) for w in out["warnings"]]
    assert ("REQUIRED_FIELD_MISSING", "confidence") in codes  # A 경고 유지
    assert any(c == "OFFICIAL_MATCH_NOT_FOUND" for c, _ in codes)  # B 경고 추가
    # 설계 한계: 계약 B 에는 A 의 status(SUCCESS/NEEDS_CONFIRMATION) 를 담을 곳이 없다 → DESIGN 문서의 결정 요청 사항
    assert "extraction_status" not in out


@pytest.mark.parametrize("bad", [None, "문자열", {"status": "MATCHED", "record": None}])
def test_s15_unsupported_input_is_failed_not_exception(bad):
    out = run(bad, [TYLE])
    check_contract(out)
    assert out["status"] == "FAILED" and out["record"] is None
