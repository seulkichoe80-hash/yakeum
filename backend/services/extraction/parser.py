"""Parse a Gemini-style JSON response without performing network I/O."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .models import ExtractedDocument, ExtractedIngredient, ExtractedMedication


class ExtractionPayloadError(ValueError):
    """Raised when a provider response cannot be safely interpreted."""


def parse_gemini_response(raw_response: str) -> ExtractedDocument:
    """Convert provider JSON into internal immutable models.

    Decimal values are parsed without a float round-trip.  Unknown values stay
    ``None``; this parser never creates product names, strengths, or doses.
    """

    if not isinstance(raw_response, str) or not raw_response.strip():
        raise ExtractionPayloadError("AI 응답이 비어 있습니다.")

    cleaned = _strip_code_fence(raw_response)
    try:
        payload = json.loads(cleaned, parse_float=Decimal)
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        raise ExtractionPayloadError("AI 응답을 JSON으로 해석할 수 없습니다.") from error

    if not isinstance(payload, Mapping):
        raise ExtractionPayloadError("AI 응답의 최상위 값은 객체여야 합니다.")

    medication_values = payload.get("medications", [])
    if not isinstance(medication_values, list):
        raise ExtractionPayloadError("medications는 배열이어야 합니다.")

    medications = tuple(_parse_medication(value) for value in medication_values)
    return ExtractedDocument(
        document_type_raw=_text(payload.get("document_type")),
        medications=medications,
        claimed_family_member_id=_text(payload.get("family_member_id")),
    )


def _strip_code_fence(raw_response: str) -> str:
    cleaned = raw_response.strip()
    if not cleaned.startswith("```"):
        return cleaned
    lines = cleaned.splitlines()
    if len(lines) < 3 or lines[-1].strip() != "```":
        raise ExtractionPayloadError("AI 응답 코드블록이 완전하지 않습니다.")
    return "\n".join(lines[1:-1]).strip()


def _parse_medication(value: Any) -> ExtractedMedication:
    if not isinstance(value, Mapping):
        raise ExtractionPayloadError("medications 항목은 객체여야 합니다.")

    ingredients_value = value.get("ingredients", [])
    if not isinstance(ingredients_value, list):
        raise ExtractionPayloadError("ingredients는 배열이어야 합니다.")

    return ExtractedMedication(
        # ``name`` is the legacy A-team raw-name key.  It remains raw data.
        product_name_raw=_text(value.get("product_name_raw")) or _text(value.get("name")),
        ingredients=tuple(_parse_ingredient(item) for item in ingredients_value),
        unit=_text(value.get("unit")),
        dose_per_administration=_decimal(value.get("dose_per_administration")),
        administrations_per_day=_decimal(value.get("administrations_per_day")),
        duration_days=_decimal(value.get("duration_days")),
        # Legacy ``instructions`` is raw dosage prose.  Ambiguous ``dosage`` is
        # deliberately not treated as product strength or administration dose.
        dosage_text_raw=(
            _text(value.get("dosage_text_raw"))
            or _text(value.get("instructions"))
            or _text(value.get("dosage"))
        ),
        confidence=_confidence(value.get("confidence")),
    )


def _parse_ingredient(value: Any) -> ExtractedIngredient:
    if not isinstance(value, Mapping):
        raise ExtractionPayloadError("ingredients 항목은 객체여야 합니다.")
    return ExtractedIngredient(
        ingredient_name_raw=(
            _text(value.get("ingredient_name_raw")) or _text(value.get("name"))
        ),
        product_strength=_decimal(value.get("product_strength")),
        product_strength_unit=_text(value.get("product_strength_unit")),
    )


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ExtractionPayloadError("문자열 필드 형식이 올바르지 않습니다.")
    stripped = value.strip()
    return stripped or None


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or isinstance(value, float):
        raise ExtractionPayloadError("Decimal 필드는 정밀도가 보존되는 값이어야 합니다.")
    try:
        decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ExtractionPayloadError("Decimal 필드 형식이 올바르지 않습니다.") from error
    if not decimal_value.is_finite() or decimal_value < 0:
        raise ExtractionPayloadError("Decimal 필드는 0 이상의 유한한 값이어야 합니다.")
    return decimal_value


def _confidence(value: Any) -> Decimal | None:
    confidence = _decimal(value)
    if confidence is not None and confidence > 1:
        raise ExtractionPayloadError("confidence는 0과 1 사이여야 합니다.")
    return confidence
