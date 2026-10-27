"""TASK A internal extraction models → shared ExtractionResult draft."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Callable

from .models import ExtractedDocument, ExtractedIngredient, ExtractedMedication, FailedMedication
from .parser import ExtractionPayloadError, parse_gemini_response

EXTRACTION_STATUSES = frozenset({"SUCCESS", "NEEDS_CONFIRMATION", "FAILED"})
SOURCE_TYPES = frozenset({"PRESCRIPTION", "MEDICINE_BAG", "SUPPLEMENT"})
RECORD_ID_NAMESPACE = uuid.UUID("fb99c074-cb35-45ca-84b6-9e7b76404723")
_SOURCE_ID_RE = re.compile(r"^[^\x00-\x1f\x7f]{1,200}$")

RecordIdFactory = Callable[[str, str], str]
ProviderCall = Callable[[], str]


@dataclass(frozen=True)
class ExtractionContext:
    """System/caller-owned fields that Gemini must never invent."""

    family_member_id: str
    source_document_id: str
    record_date: str


def adapt_gemini_response(
    raw_response: str,
    context: ExtractionContext,
    *,
    record_id_factory: RecordIdFactory | None = None,
) -> list[dict[str, Any]]:
    """Return one shared ExtractionResult per medication candidate."""

    try:
        document = parse_gemini_response(raw_response)
        return adapt_extracted_document(
            document,
            context,
            record_id_factory=record_id_factory,
        )
    except (ExtractionPayloadError, ValueError, TypeError):
        return [_failed_result("AI 응답을 공통 추출 결과로 변환할 수 없습니다.")]


def adapt_provider_call(
    provider_call: ProviderCall,
    context: ExtractionContext,
    *,
    record_id_factory: RecordIdFactory | None = None,
) -> list[dict[str, Any]]:
    """Call an injected provider and sanitize every provider exception.

    Production Gemini wiring is intentionally absent in this PoC.  Tests inject
    a fake callable, so this function performs no external I/O by itself.
    """

    try:
        raw_response = provider_call()
    except Exception:  # Provider messages may contain credentials or user data.
        return [_failed_result("AI 인식 요청을 완료하지 못했습니다.")]
    return adapt_gemini_response(
        raw_response,
        context,
        record_id_factory=record_id_factory,
    )


def adapt_extracted_document(
    document: ExtractedDocument,
    context: ExtractionContext,
    *,
    record_id_factory: RecordIdFactory | None = None,
) -> list[dict[str, Any]]:
    try:
        family_member_id, source_document_id, record_date = _validate_context(context)
    except ValueError:
        return [_failed_result("호출자 필수 정보를 확인할 수 없습니다.")]

    if (
        document.claimed_family_member_id is not None
        and document.claimed_family_member_id != family_member_id
    ):
        return [_failed_result("응답의 가족 범위가 요청과 일치하지 않습니다.")]

    source_type = _source_type(document.document_type_raw)
    if not document.medications:
        return [_needs_confirmation(None, "제품 정보를 확인할 수 없습니다.", "product_name_raw")]

    results: list[dict[str, Any]] = []
    for index, medication in enumerate(document.medications, start=1):
        if isinstance(medication, FailedMedication):
            results.append(_failed_result(f"후보 {index}의 정보 형식을 확인할 수 없습니다. 원본을 확인하고 다시 처리해 주세요."))
            continue
        if source_type is None:
            results.append(
                _needs_confirmation(None, "자료 유형을 확인할 수 없습니다.", "source_type")
            )
            continue
        if medication.product_name_raw is None:
            results.append(
                _needs_confirmation(None, "제품명을 확인할 수 없습니다.", "product_name_raw")
            )
            continue

        source_record_id = f"{source_document_id}:{index}"
        record_id = (record_id_factory or default_record_id)(
            family_member_id,
            source_record_id,
        )
        try:
            record_id = str(uuid.UUID(str(record_id)))
        except ValueError:
            results.append(_failed_result("시스템 record_id를 생성할 수 없습니다."))
            continue

        warnings: list[dict[str, str | None]] = []
        if medication.confidence is None:
            warnings.append(
                _error_detail(
                    "REQUIRED_FIELD_MISSING",
                    "AI 신뢰도를 확인할 수 없습니다.",
                    "confidence",
                )
            )
        if not medication.ingredients:
            warnings.append(
                _error_detail(
                    "REQUIRED_FIELD_MISSING",
                    "성분 정보를 확인할 수 없어 사용자 확인이 필요합니다.",
                    "ingredients",
                )
            )
        for ingredient_index, ingredient in enumerate(medication.ingredients):
            if (ingredient.ingredient_name_raw is None
                    or ingredient.product_strength is None
                    or ingredient.product_strength_unit is None):
                warnings.append(_error_detail(
                    "REQUIRED_FIELD_MISSING",
                    f"성분 {ingredient_index + 1}의 이름·함량·단위 중 미확인 정보가 있습니다. 원본을 확인해 주세요.",
                    f"ingredients[{ingredient_index}]",
                ))
            if ingredient.product_strength is not None and ingredient.product_strength_unit is None:
                warnings.append(
                    _error_detail(
                        "REQUIRED_FIELD_MISSING",
                        "제품 함량 단위를 확인할 수 없습니다.",
                        "ingredients",
                    )
                )

        record = _medication_record(
            medication,
            family_member_id=family_member_id,
            source_type=source_type,
            source_record_id=source_record_id,
            record_id=record_id,
            record_date=record_date,
        )
        results.append(
            {
                "status": "NEEDS_CONFIRMATION" if warnings else "SUCCESS",
                "record": record,
                "warnings": warnings,
                "errors": [],
            }
        )
    return results


def default_record_id(family_member_id: str, source_record_id: str) -> str:
    """System-owned deterministic identifier; Gemini never supplies it."""

    return str(uuid.uuid5(RECORD_ID_NAMESPACE, f"{family_member_id}|{source_record_id}"))


def _validate_context(context: ExtractionContext) -> tuple[str, str, str]:
    family_member_id = str(uuid.UUID(str(context.family_member_id)))
    source_document_id = str(context.source_document_id).strip()
    if not _SOURCE_ID_RE.fullmatch(source_document_id):
        raise ValueError("source_document_id is required")
    record_date = str(context.record_date).strip()
    try:
        if date.fromisoformat(record_date).isoformat() != record_date:
            raise ValueError("record_date must be canonical")
    except ValueError as error:
        raise ValueError("record_date must be YYYY-MM-DD") from error
    return family_member_id, source_document_id, record_date


def _source_type(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    aliases = {
        "PRESCRIPTION": "PRESCRIPTION",
        "처방전": "PRESCRIPTION",
        "MEDICINE_BAG": "MEDICINE_BAG",
        "PILL_ENVELOPE": "MEDICINE_BAG",
        "약봉투": "MEDICINE_BAG",
        "SUPPLEMENT": "SUPPLEMENT",
        "HEALTH_SUPPLEMENT": "SUPPLEMENT",
        "건강기능식품": "SUPPLEMENT",
    }
    return aliases.get(raw_value.strip())


def _medication_record(
    medication: ExtractedMedication,
    *,
    family_member_id: str,
    source_type: str,
    source_record_id: str,
    record_id: str,
    record_date: str,
) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "family_member_id": family_member_id,
        "source_type": source_type,
        "source_record_id": source_record_id,
        "record_date": record_date,
        "dispensing_date": None,
        "prescribing_institution": None,
        "dispensing_institution": None,
        "product_name_raw": medication.product_name_raw,
        "product_name_normalized": None,
        "drug_code": None,
        "drug_category": None,
        "unit": medication.unit,
        "dose_per_administration": _decimal_text(medication.dose_per_administration),
        "administrations_per_day": _decimal_text(medication.administrations_per_day),
        "duration_days": _decimal_text(medication.duration_days),
        "dosage_text_raw": medication.dosage_text_raw,
        "mfds_product_id": None,
        "ingredients": [_ingredient(value) for value in medication.ingredients],
        "confidence": _decimal_text(medication.confidence),
        "user_confirmed": False,
    }


def _ingredient(value: ExtractedIngredient) -> dict[str, str | None]:
    return {
        "ingredient_name_raw": value.ingredient_name_raw,
        "ingredient_name_normalized": None,
        "product_strength": _decimal_text(value.product_strength),
        "product_strength_unit": value.product_strength_unit,
        "official_ingredient_id": None,
    }


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def _needs_confirmation(
    record: dict[str, Any] | None,
    message: str,
    field: str,
) -> dict[str, Any]:
    return {
        "status": "NEEDS_CONFIRMATION",
        "record": record,
        "warnings": [_error_detail("REQUIRED_FIELD_MISSING", message, field)],
        "errors": [],
    }


def _failed_result(message: str) -> dict[str, Any]:
    return {
        "status": "FAILED",
        "record": None,
        "warnings": [],
        "errors": [_error_detail("AI_EXTRACTION_FAILED", message, None)],
    }


def _error_detail(code: str, message: str, field: str | None) -> dict[str, str | None]:
    return {"code": code, "message": message, "field": field}
