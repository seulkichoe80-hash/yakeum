"""D-side Gemini wiring for the existing extraction contract, without an endpoint.

No network I/O occurs at import time. Callers must supply a virtual/de-identified
image and caller-owned context. Results remain unconfirmed extraction candidates.
"""

from __future__ import annotations

from typing import Any

from backend.services.extraction import (
    ExtractionContext,
    GeminiSettings,
    adapt_provider_call,
)

MAX_IMAGE_BYTES = 10 * 1024 * 1024
IMAGE_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})


def extract_image_candidates(
    image_bytes: bytes,
    mime_type: str,
    context: ExtractionContext,
) -> list[dict[str, Any]]:
    """Return existing ExtractionResult dictionaries; never persist or log input.

    Configuration, SDK and provider failures are sanitized by adapt_provider_call.
    This callable is not an upload API and does not normalize, save or confirm.
    """
    # Reject invalid caller-owned scope before any external request.
    from backend.services.extraction.adapter import _validate_context

    try:
        _validate_context(context)
    except (ValueError, TypeError, AttributeError):
        return _failed("호출자 필수 정보를 확인할 수 없습니다.")
    if (
        not isinstance(image_bytes, bytes)
        or not image_bytes
        or len(image_bytes) > MAX_IMAGE_BYTES
        or mime_type not in IMAGE_MIME_TYPES
    ):
        return _failed("이미지 형식 또는 크기를 확인해 주세요.")

    def request() -> str:
        settings = GeminiSettings.from_environment()
        return _request_gemini(image_bytes, mime_type, settings)

    return adapt_provider_call(request, context)


def _request_gemini(image_bytes: bytes, mime_type: str, settings: GeminiSettings) -> str:
    from backend.services.extraction.sdk import request_image

    return request_image(image_bytes, mime_type, settings)


def _failed(message: str) -> list[dict[str, Any]]:
    return [{
        "status": "FAILED", "record": None, "warnings": [],
        "errors": [{"code": "AI_EXTRACTION_FAILED", "message": message, "field": None}],
    }]
