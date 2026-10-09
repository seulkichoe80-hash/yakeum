"""B 내부 NormalizationResult → 약이음 공통 규격(docs/DATA_SCHEMA.md, docs/API_CONTRACT.md) 변환 계층.

parser/service 의 내부 모델은 그대로 두고, 팀 간 전달 형태는 이 모듈만 책임진다.
공통 문서의 Schema/Contract 는 바꾸지 않는다 (필드명·상태값·ErrorDetail 구조를 그대로 따른다).

생성 주체 (DATA_SCHEMA TODO 항목 — 팀장 확인 전까지의 B 측 잠정 규칙, 모두 주입 가능):
- family_member_id : 호출자(API/D)가 반드시 넘긴다. B 는 만들거나 추측하지 않는다 (없으면 ValueError).
- record_id        : 시스템 생성 UUID. 기본값은 (family_member_id, source_type, source_record_id) 기반
                     uuid5 라서 같은 파일을 다시 올려도 같은 ID 가 된다. record_id_factory 로 교체 가능.
- source_record_id : "hira:" + 원본 행 값의 SHA-256 앞 20자 (+ 동일 내용 행이 반복되면 "-2", "-3"…).
                     행 번호·파일명에 의존하지 않으므로 재다운로드·재업로드에도 안정적이다.
- record_date      : HIRA 는 dispensing_date(조제일자). 없으면 추측하지 않고 FAILED(record=null) 처리한다.
- user_confirmed   : False (사용자 확인 전). confidence : null (HIRA 는 AI 입력이 아님).
- 수량(Decimal)    : float 를 거치지 않고 문자열("1", "0.5")로 직렬화한다.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.services.normalization.models import (
    STATUS_FAILED,
    Ingredient,
    MedicationRecord,
    NormalizationResult,
    decimal_to_str,
)

SOURCE_TYPE_HIRA = "HIRA"
RECORD_ID_NAMESPACE = uuid.UUID("6b1f4c1e-5a0d-4c53-9d3e-2f0a7b8c9d10")  # 약이음 B (고정값)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

RecordIdFactory = Callable[[str, str, str], str]  # (family_member_id, source_type, source_record_id) -> UUID 문자열


# ----------------------------------------------------------------------------- 식별자
def _require_uuid(value: Any, name: str) -> str:
    if value is None:
        raise ValueError(f"{name} 는 호출자가 제공해야 합니다 (B 는 생성하거나 추측하지 않음)")
    try:
        return str(uuid.UUID(str(value)))
    except ValueError as e:
        raise ValueError(f"{name} 가 UUID 형식이 아님: {value!r}") from e


def default_record_id(family_member_id: str, source_type: str, source_record_id: str) -> str:
    return str(uuid.uuid5(RECORD_ID_NAMESPACE, f"{family_member_id}|{source_type}|{source_record_id}"))


def source_record_key(rec: MedicationRecord) -> str:
    """원본 행의 내용만으로 만든 안정 키 (occurrence 제외).

    행 번호·'번호' 컬럼·파일명·셀 서식(datetime/문자열)에 영향받지 않도록 파싱된 값(날짜는 YYYY-MM-DD,
    수량은 Decimal 문자열)으로 만든다.
    """
    d = rec.dosage
    fields = [
        rec.dispensing_date or rec.dispensing_date_raw, rec.date or rec.date_raw, rec.drug_code,
        rec.product_name.raw, rec.prescribing_institution, rec.dispensing_institution, rec.institution,
        rec.drug_category, rec.unit,
        [i.name.raw for i in rec.ingredients if i.source == "HIRA"],
        [None if v is None else decimal_to_str(v) for v in (d.dose_per_time, d.times_per_day, d.total_days)],
    ]
    payload = json.dumps(fields, ensure_ascii=False, separators=(",", ":"))
    return "hira:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


# ----------------------------------------------------------------------------- ErrorDetail
# 공통 오류 코드는 API_CONTRACT 의 초기 5종만 사용한다. 의미가 맞는 코드가 없는 파싱 경고는
# NORMALIZATION_FAILED 로 두고 field/message 로 구분한다. (새 코드 추가는 팀 협의 필요)
_FIELD_BY_INTERNAL = {
    "product_name": "product_name_raw",
    "dispensing_date": "dispensing_date",
    "date": "record_date",
    "drug_code": "drug_code",
    "dose_per_time": "dose_per_administration",
    "times_per_day": "administrations_per_day",
    "total_days": "duration_days",
}

_RULES: List[Tuple[Callable[[str], bool], str, Optional[str]]] = [
    (lambda m: m.startswith(("파일을 읽을 수 없음", "헤더 행을 찾을 수 없음")), "INVALID_FILE_FORMAT", None),
    (lambda m: m.startswith("필수 컬럼 없음"), "REQUIRED_FIELD_MISSING", None),
    (lambda m: m.startswith("약품명이 비어"), "REQUIRED_FIELD_MISSING", "product_name_raw"),
    (lambda m: m.startswith(("공식 데이터", "후보 ")), "OFFICIAL_MATCH_NOT_FOUND", None),
    (lambda m: m.startswith("약품코드"), "NORMALIZATION_FAILED", "drug_code"),
    (lambda m: m.startswith(("이상 날짜", "날짜 없음")), "NORMALIZATION_FAILED", "record_date"),
    (lambda m: m.startswith("dispensing_date"), "NORMALIZATION_FAILED", "dispensing_date"),
    (lambda m: m.startswith(tuple(f"{k}:" for k in ("dose_per_time", "times_per_day", "total_days"))), "NORMALIZATION_FAILED", None),
    (lambda m: any(k in m for k in ("성분", "함량")), "NORMALIZATION_FAILED", "ingredients"),
]


def to_error_detail(message: str, default_code: str = "NORMALIZATION_FAILED") -> Dict[str, Optional[str]]:
    """B 내부 문자열 경고/오류 → {code, message, field}. 알 수 없는 문구는 원문을 보존한다."""
    for pred, code, field in _RULES:
        if pred(message):
            if field is None:
                m = re.match(r"^(dose_per_time|times_per_day|total_days):", message)
                if m:
                    field = _FIELD_BY_INTERNAL[m.group(1)]
            return {"code": code, "message": message, "field": field}
    return {"code": default_code, "message": message, "field": None}


# ----------------------------------------------------------------------------- 변환
def _dec(v: Optional[Decimal]) -> Optional[str]:
    return None if v is None else decimal_to_str(v)


def _ingredient(ing: Ingredient) -> Dict[str, Any]:
    from_official = ing.source == "MFDS"
    return {
        # 공식 데이터에서 보완된 성분은 원본(raw)에서 확인한 값이 아니므로 raw 를 비운다.
        "ingredient_name_raw": None if from_official else ing.name.raw,
        "ingredient_name_normalized": ing.name.raw if from_official else ing.name.normalized,
        "product_strength": _dec(ing.amount),
        "product_strength_unit": ing.unit,
        "official_ingredient_id": ing.official_id,
    }


def _record(rec: MedicationRecord, result: NormalizationResult, family_member_id: str,
            source_record_id: str, record_id: str) -> Dict[str, Any]:
    d = rec.dosage
    return {
        "record_id": record_id,
        "family_member_id": family_member_id,
        "source_type": SOURCE_TYPE_HIRA,
        "source_record_id": source_record_id,
        "record_date": rec.dispensing_date,
        "dispensing_date": rec.dispensing_date,
        "prescribing_institution": rec.prescribing_institution,
        "dispensing_institution": rec.dispensing_institution,
        "product_name_raw": rec.product_name.raw,
        "product_name_normalized": rec.official_name or rec.product_name.normalized,
        "drug_code": rec.drug_code,
        "drug_category": rec.drug_category,
        "unit": rec.unit,
        "dose_per_administration": _dec(d.dose_per_time),
        "administrations_per_day": _dec(d.times_per_day),
        "duration_days": _dec(d.total_days),
        "dosage_text_raw": None,  # HIRA 는 복용법 문구가 없다
        # 식약처 제품 ID 는 단일 매칭 결과만 사용한다 (후보 여러 건이면 null). HIRA 약품코드와 별개다.
        "mfds_product_id": result.match.official_id,
        "ingredients": [_ingredient(i) for i in rec.ingredients],
        "confidence": None,
        "user_confirmed": False,
    }


def _null_match() -> Dict[str, Optional[str]]:
    return {"source": None, "official_id": None, "match_method": None}


def to_common_result(
    result: NormalizationResult,
    family_member_id: str,
    occurrence: int = 1,
    record_id_factory: Optional[RecordIdFactory] = None,
) -> Dict[str, Any]:
    """NormalizationResult 1건 → API_CONTRACT Contract B 형태의 dict (JSON 직렬화 가능)."""
    fid = _require_uuid(family_member_id, "family_member_id")
    warnings = [to_error_detail(w) for w in result.warnings]
    errors = [to_error_detail(e) for e in result.errors]
    rec = result.record

    if result.status != STATUS_FAILED and not errors:
        if rec.dispensing_date is None:  # HIRA 필수 필드: 대표 기준일을 추측하지 않는다
            errors.append({
                "code": "REQUIRED_FIELD_MISSING",
                "message": "조제일자를 확인할 수 없어 공통 MedicationRecord 를 만들 수 없습니다.",
                "field": "dispensing_date",
            })
        if rec.product_name.raw is None:
            errors.append({"code": "REQUIRED_FIELD_MISSING", "message": "제품명을 확인할 수 없습니다.", "field": "product_name_raw"})

    if result.status == STATUS_FAILED or errors:
        # 계약: FAILED 는 record=null. 원본 행 값은 B 내부 결과(raw_row)에만 남는다.
        return {"status": STATUS_FAILED, "record": None, "match": _null_match(), "warnings": warnings, "errors": errors}

    key = source_record_key(rec)
    source_record_id = key if occurrence <= 1 else f"{key}-{occurrence}"
    rid = (record_id_factory or default_record_id)(fid, SOURCE_TYPE_HIRA, source_record_id)
    match = {
        "source": result.match.source,
        "official_id": result.match.official_id,
        "match_method": None if result.match.match_method == "NONE" else result.match.match_method,
    }
    return {
        "status": result.status,
        "record": _record(rec, result, fid, source_record_id, _require_uuid(rid, "record_id")),
        "match": match,
        "warnings": warnings,
        "errors": [],
    }


def to_common_results(
    results: List[NormalizationResult],
    family_member_id: str,
    record_id_factory: Optional[RecordIdFactory] = None,
) -> List[Dict[str, Any]]:
    """파일 1개 분량의 결과를 변환. 같은 내용의 행이 반복되면 occurrence 로 source_record_id 를 구분한다."""
    seen: Dict[str, int] = {}
    out = []
    for r in results:
        n = 1
        if r.status != STATUS_FAILED:
            k = source_record_key(r.record)
            seen[k] = n = seen.get(k, 0) + 1
        out.append(to_common_result(r, family_member_id, n, record_id_factory))
    return out


# ----------------------------------------------------------------------------- 계약 점검
RECORD_KEYS = (
    "record_id family_member_id source_type source_record_id record_date dispensing_date "
    "prescribing_institution dispensing_institution product_name_raw product_name_normalized drug_code "
    "drug_category unit dose_per_administration administrations_per_day duration_days dosage_text_raw "
    "mfds_product_id ingredients confidence user_confirmed"
).split()
INGREDIENT_KEYS = ("ingredient_name_raw ingredient_name_normalized product_strength "
                   "product_strength_unit official_ingredient_id").split()
_DECIMAL_FIELDS = ("dose_per_administration", "administrations_per_day", "duration_days")
_DEC_RE = re.compile(r"^-?\d+(\.\d+)?$")


def validate_common_result(res: Dict[str, Any]) -> List[str]:
    """DATA_SCHEMA/API_CONTRACT 형태 점검. 문제 문구 목록(비어 있으면 통과)."""
    p: List[str] = []
    if set(res) != {"status", "record", "match", "warnings", "errors"}:
        p.append(f"최상위 키 불일치: {sorted(res)}")
    if res.get("status") not in ("MATCHED", "PARTIAL", "UNMATCHED", "FAILED"):
        p.append(f"status 값 오류: {res.get('status')!r}")
    if set(res.get("match") or {}) != {"source", "official_id", "match_method"}:
        p.append("match 키 불일치")
    for kind in ("warnings", "errors"):
        for e in res.get(kind, []):
            if set(e) != {"code", "message", "field"}:
                p.append(f"{kind} 항목이 ErrorDetail 형식이 아님: {e}")
    rec = res.get("record")
    if res.get("status") == "FAILED":
        if rec is not None:
            p.append("FAILED 인데 record 가 null 이 아님")
        return p
    if rec is None:
        return p + ["FAILED 가 아닌데 record 가 null"]
    if list(rec) != RECORD_KEYS:
        p.append(f"record 키/순서 불일치: {sorted(set(rec) ^ set(RECORD_KEYS))}")
    for k in ("record_id", "family_member_id"):
        try:
            uuid.UUID(str(rec.get(k)))
        except ValueError:
            p.append(f"{k} 가 UUID 가 아님")
    for k in ("record_date", "dispensing_date"):
        if rec.get(k) is not None and not _DATE_RE.match(str(rec[k])):
            p.append(f"{k} 형식 오류")
    if rec.get("source_type") == "HIRA" and not rec.get("dispensing_date"):
        p.append("HIRA 는 dispensing_date 필수")
    for k in ("source_record_id", "product_name_raw"):
        if not rec.get(k):
            p.append(f"{k} 누락")
    for k in _DECIMAL_FIELDS:
        v = rec.get(k)
        if v is not None and not (isinstance(v, str) and _DEC_RE.match(v)):
            p.append(f"{k} 는 Decimal 문자열이어야 함: {v!r}")
    if rec.get("drug_code") is not None and not isinstance(rec["drug_code"], str):
        p.append("drug_code 는 String 이어야 함")
    if not isinstance(rec.get("user_confirmed"), bool):
        p.append("user_confirmed 는 bool")
    if not isinstance(rec.get("ingredients"), list):
        p.append("ingredients 는 배열")
    else:
        for i in rec["ingredients"]:
            if list(i) != INGREDIENT_KEYS:
                p.append(f"Ingredient 키 불일치: {sorted(set(i) ^ set(INGREDIENT_KEYS))}")
            sv = i.get("product_strength")
            if sv is not None and not (isinstance(sv, str) and _DEC_RE.match(sv)):
                p.append(f"product_strength 는 Decimal 문자열이어야 함: {sv!r}")
            if sv is not None and not i.get("product_strength_unit"):
                p.append("product_strength 가 있으면 product_strength_unit 필요")
    return p
