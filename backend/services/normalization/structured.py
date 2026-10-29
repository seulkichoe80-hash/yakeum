"""Structured extraction input using B's existing matcher and team contracts.

The D integration calls this separately from the unchanged HIRA parser. It never
confirms a user decision, mutates the source or invokes a default live client.
"""

from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping
from uuid import UUID

from .adapter import RECORD_KEYS, validate_common_result, to_error_detail
from .matcher import match
from .name_normalizer import normalize_name


def _failed(warnings, errors):
    return {"status": "FAILED", "record": None,
            "match": {"source": None, "official_id": None, "match_method": None},
            "warnings": warnings, "errors": errors}


def normalize_structured_record(extraction_result: Mapping[str, Any], client, *,
                                expected_family_member_id: str,
                                threshold: float = 0.9) -> dict[str, Any]:
    """A result -> B result. Explicit injected client keeps offline runs offline."""
    error = {"code": "NORMALIZATION_FAILED", "message": "추출 결과의 형식 또는 가족 정보를 확인해 주세요.", "field": None}
    if not isinstance(extraction_result, Mapping) or extraction_result.get("status") not in {"SUCCESS", "NEEDS_CONFIRMATION", "FAILED"}:
        return _failed([], [error])
    try:
        warnings = deepcopy(list(extraction_result.get("warnings", [])))
        errors = deepcopy(list(extraction_result.get("errors", [])))
        for item in warnings + errors:
            if not isinstance(item, dict) or set(item) != {"code", "message", "field"}:
                return _failed([], [error])
            if not isinstance(item["code"], str) or not isinstance(item["message"], str) or (item["field"] is not None and not isinstance(item["field"], str)):
                return _failed([], [error])
        if extraction_result["status"] == "FAILED":
            return _failed(warnings, errors or [error])
        src = extraction_result.get("record")
        if not isinstance(src, Mapping):
            return _failed(warnings, errors or [{**error, "message": "정규화할 후보 기록이 없습니다."}])
        record = {key: deepcopy(src[key]) for key in RECORD_KEYS}
        if set(src) != set(RECORD_KEYS) or record["family_member_id"] != expected_family_member_id:
            return _failed(warnings, [error])
        UUID(record["record_id"]); UUID(record["family_member_id"])
        if record["source_type"] not in {"MEDICINE_BAG", "PRESCRIPTION", "SUPPLEMENT"}:
            return _failed(warnings, [error])
        date.fromisoformat(record["record_date"])
        check = {"status": "UNMATCHED", "record": record,
                 "match": {"source": None, "official_id": None, "match_method": None},
                 "warnings": warnings, "errors": errors}
        if validate_common_result(check):
            return _failed(warnings, [error])
        if not isinstance(record["source_record_id"], str) or not record["source_record_id"].strip():
            return _failed(warnings, [error])
        for ingredient in record["ingredients"]:
            for field in ("ingredient_name_raw", "ingredient_name_normalized", "product_strength_unit", "official_ingredient_id"):
                if ingredient[field] is not None and not isinstance(ingredient[field], str):
                    return _failed(warnings, [error])
            strength = ingredient["product_strength"]
            if strength is not None and (not Decimal(strength).is_finite() or Decimal(strength) < 0):
                return _failed(warnings, [error])
        if not isinstance(record["product_name_raw"], str) or not record["product_name_raw"].strip():
            return _failed(warnings, [error])
        for field in ("dose_per_administration", "administrations_per_day", "duration_days", "confidence"):
            val = record[field]
            if val is not None:
                num = Decimal(val)
                if not num.is_finite() or num < 0 or (field == "confidence" and num > 1):
                    return _failed(warnings, [error])
        if not 0 < threshold <= 1:
            return _failed(warnings, [error])
    except (KeyError, TypeError, ValueError, AttributeError, InvalidOperation):
        return _failed([], [error])

    # Keep the original and the edited snapshot outside this result; do not
    # replace raw values with normalized/official names.
    record["product_name_normalized"] = normalize_name(record["product_name_raw"])
    for ing in record["ingredients"]:
        ing["ingredient_name_normalized"] = normalize_name(ing["ingredient_name_raw"])
    result = {"status": "UNMATCHED", "record": record,
              "match": {"source": None, "official_id": None, "match_method": None},
              "warnings": warnings, "errors": errors}
    try:
        outcome = match(client, None, record["product_name_raw"], threshold)
    except Exception:
        warnings.append(to_error_detail("공식 데이터 조회 실패 (원본 값 보존)"))
        return result
    # Do not relay arbitrary client exception strings or secret-bearing warnings.
    if outcome.warnings or outcome.lookup_failed:
        warnings.append(to_error_detail("제품 조회 경고가 있습니다. 원본을 확인해 주세요."))
    if outcome.lookup_failed:
        # A partial service failure cannot establish uniqueness across sources.
        return result
    if not outcome.candidates:
        warnings.append(to_error_detail("공식 데이터에서 찾지 못함 (원본 값 보존)"))
    elif len(outcome.candidates) > 1:
        result["status"] = "PARTIAL"
        result["match"]["match_method"] = outcome.method
        warnings.append(to_error_detail("복수 제품 후보가 있어 자동 확정하지 않았습니다."))
    else:
        item = outcome.candidates[0]
        result["status"] = "MATCHED"
        result["match"] = {"source": item.source, "official_id": item.official_id, "match_method": outcome.method}
        record["mfds_product_id"] = item.official_id
        record["product_name_normalized"] = item.name
        if item.source == "MFDS_DRUG" and outcome.method in {"NAME_EXACT", "NAME_FUZZY"}:
            # Product-name normalization removes strength text. A single name
            # candidate is not evidence that ingredients or strength agree.
            warnings.append(to_error_detail(
                "제품명 기준 단일 후보 매칭입니다. 성분·함량·단위의 공식 일치 검증은 수행하지 않았습니다. 원본과 후보를 확인해 주세요."
            ))
        if not record["ingredients"]:
            # Empty-ingredient contract and official-strength supplementation
            # remain unresolved. Preserve the empty list rather than fabricate.
            result["status"] = "PARTIAL"
            warnings.append(to_error_detail("성분 원본이 없어 비교를 보류해야 합니다."))
    return result
