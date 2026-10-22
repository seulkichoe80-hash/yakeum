# extraction.py
# 약이음 Task A - Gemini API 이미지 분석 및 약 정보 추출

import os
import json
import math
from pathlib import Path

if __package__:
    from .schema import DocumentType, MealTiming, MedicationItem, ExtractionResult
    from .prompt import SYSTEM_PROMPT
else:
    from schema import DocumentType, MealTiming, MedicationItem, ExtractionResult
    from prompt import SYSTEM_PROMPT


def _confidence(value):
    # Preserve the existing schema's -1 sentinel for unavailable confidence.
    if value is None or value == -1:
        return -1.0
    if isinstance(value, bool):
        raise ValueError('Invalid confidence')
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise ValueError('Invalid confidence')
    return number


def _request_image(image_bytes, mime_type, model_name, api_key):
    if __package__:
        from .config import GeminiSettings
        from .sdk import request_image
    else:
        # File execution is supported without importing a top-level schema module
        # from another folder. The common provider should normally be used.
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
        from backend.services.extraction.config import GeminiSettings
        from backend.services.extraction.sdk import request_image
    return request_image(image_bytes, mime_type, GeminiSettings(model_name, api_key))


# ─────────────────────────────────────
# JSON 파싱 → ExtractionResult 변환
# ─────────────────────────────────────
def _parse_response(raw_json: str) -> ExtractionResult:
    """Gemini 응답 JSON을 ExtractionResult 객체로 변환"""

    # 코드블록 제거 (```json ... ``` 형태 대비)
    if not isinstance(raw_json, str) or not raw_json.strip():
        raise ValueError('Empty response')
    cleaned = raw_json.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        if len(lines) < 3 or lines[-1].strip() != "```":
            raise ValueError("Incomplete code fence")
        cleaned = "\n".join(lines[1:-1])

    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError('Response must be an object')
    if data.get('error_message'):
        raise ValueError('Provider reported failure')
    items = data.get('medications')
    if not isinstance(items, list) or not items:
        raise ValueError('No medication candidates')

    # ── document_type 변환 ──
    doc_type_map = {
        "처방전": DocumentType.PRESCRIPTION,
        "약봉투": DocumentType.PILL_ENVELOPE,
        "건강기능식품": DocumentType.HEALTH_SUPPLEMENT,
    }
    raw_doc_type = data.get("document_type")
    if raw_doc_type is None:
        raise ValueError("document_type 누락: AI 응답에 문서 종류가 없습니다")
    document_type = doc_type_map.get(raw_doc_type)
    if document_type is None:
        raise ValueError(f"document_type 알 수 없음: '{raw_doc_type}'")

    # ── timing 변환 ──
    timing_map = {
        "식전": MealTiming.BEFORE_MEAL,
        "식후": MealTiming.AFTER_MEAL,
        "식중": MealTiming.WITH_MEAL,
        "식사무관": MealTiming.REGARDLESS,
        "취침전": MealTiming.BEDTIME,
        "알수없음": MealTiming.UNKNOWN,
    }

    # ── medications 변환 ──
    medications = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Invalid medication")
        timing = timing_map.get(
            item.get("timing", "알수없음"),
            MealTiming.UNKNOWN
        )
        raw_name = item.get("product_name_raw") or item.get("name")
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise ValueError("medications[].name 누락: 약 이름이 없습니다")
        medications.append(MedicationItem(
            name=raw_name,
            dosage=item.get("dosage"),
            frequency=item.get("frequency"),
            duration=item.get("duration"),
            timing=timing,
            instructions=item.get("dosage_text_raw") or item.get("instructions"),
            confidence=_confidence(item.get("confidence")),
        ))

    return ExtractionResult(
        document_type=document_type,
        medications=medications,
        patient_name=data.get("patient_name"),
        hospital_name=data.get("hospital_name"),
        prescription_date=data.get("prescription_date"),
        raw_text=data.get("raw_text"),
        overall_confidence=_confidence(data.get("overall_confidence")),
        error_message=data.get("error_message"),
    )



# ─────────────────────────────────────
# 핵심 함수: 이미지 → ExtractionResult
# ─────────────────────────────────────
def extract_medicine_info(image_path: str) -> ExtractionResult:
    """Extract using one explicitly configured model; never log provider errors.

    No dotenv loading or external requests occur during import. The caller must
    set GEMINI_API_KEY and YAKEUM_GEMINI_MODEL in the process environment.
    """
    def failed(message):
        return ExtractionResult(document_type=DocumentType.PILL_ENVELOPE,
                                error_message=message)

    mime_map = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                '.png': 'image/png', '.webp': 'image/webp'}
    try:
        path = Path(image_path)
        mime_type = mime_map.get(path.suffix.lower())
        if mime_type is None or not path.is_file():
            return failed('이미지 파일 형식 또는 경로를 확인해 주세요.')
        if not 0 < path.stat().st_size <= 10 * 1024 * 1024:
            return failed('이미지는 0바이트 초과 10MiB 이하여야 합니다.')
        with path.open('rb') as source:
            image_bytes = source.read(10 * 1024 * 1024 + 1)
        if not 0 < len(image_bytes) <= 10 * 1024 * 1024:
            return failed('이미지 크기를 확인해 주세요.')
    except (OSError, TypeError, ValueError):
        return failed('이미지 파일을 읽을 수 없습니다.')

    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    model_name = os.environ.get('YAKEUM_GEMINI_MODEL', '').strip()
    if not api_key or not model_name:
        return failed('GEMINI_API_KEY와 YAKEUM_GEMINI_MODEL 설정이 필요합니다.')
    try:
        raw_text = _request_image(image_bytes, mime_type, model_name, api_key)
    except Exception:
        return failed('AI 인식 요청을 완료하지 못했습니다. 설정과 SDK를 확인해 주세요.')
    try:
        return _parse_response(raw_text)
    except (ValueError, TypeError, AttributeError, OverflowError):
        return failed('AI 응답을 해석할 수 없습니다. 사용자 확인이 필요합니다.')
