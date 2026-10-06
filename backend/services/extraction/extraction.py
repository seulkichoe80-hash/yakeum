# extraction.py
# 약이음 Task A - Gemini API 이미지 분석 및 약 정보 추출

import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

from schema import (
    DocumentType, MealTiming,
    MedicationItem, ExtractionResult
)
from prompt import SYSTEM_PROMPT

# ─────────────────────────────────────
# 환경 변수 로드
# ─────────────────────────────────────
load_dotenv()

# ─────────────────────────────────────
# 모델 우선순위 (503 대비 폴백)
# ─────────────────────────────────────
MODELS = [
    "gemini-3.8-flash",       # 1순위: Google 권장 최신 모델
    "gemini-3.5-flash",       # 2순위: 폴백
    "gemini-3.1-pro-preview", # 3순위: 고성능 폴백  
]

# ─────────────────────────────────────
# 클라이언트 초기화
# ─────────────────────────────────────
def _get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("❌ .env 파일에 GEMINI_API_KEY가 없습니다!")
    return genai.Client(api_key=api_key)


# ─────────────────────────────────────
# JSON 파싱 → ExtractionResult 변환
# ─────────────────────────────────────
def _parse_response(raw_json: str) -> ExtractionResult:
    """Gemini 응답 JSON을 ExtractionResult 객체로 변환"""

    # 코드블록 제거 (```json ... ``` 형태 대비)
    cleaned = raw_json.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1])

    data = json.loads(cleaned)

    # ── document_type 변환 ──
    doc_type_map = {
        "처방전": DocumentType.PRESCRIPTION,
        "약봉투": DocumentType.PILL_ENVELOPE,
        "건강기능식품": DocumentType.HEALTH_SUPPLEMENT,
    }
    document_type = doc_type_map.get(
        data.get("document_type", ""),
        DocumentType.PILL_ENVELOPE  # 기본값
    )

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
    for item in data.get("medications", []):
        timing = timing_map.get(
            item.get("timing", "알수없음"),
            MealTiming.UNKNOWN
        )
        medications.append(MedicationItem(
            name=item.get("name", "이름없음"),
            dosage=item.get("dosage"),
            frequency=item.get("frequency"),
            duration=item.get("duration"),
            timing=timing,
            instructions=item.get("instructions"),
            confidence=float(item.get("confidence", 1.0)),
        ))

    return ExtractionResult(
        document_type=document_type,
        medications=medications,
        patient_name=data.get("patient_name"),
        hospital_name=data.get("hospital_name"),
        prescription_date=data.get("prescription_date"),
        raw_text=data.get("raw_text"),
        overall_confidence=float(data.get("overall_confidence", 1.0)),
        error_message=data.get("error_message"),
    )


# ─────────────────────────────────────
# 핵심 함수: 이미지 → ExtractionResult
# ─────────────────────────────────────
def extract_medicine_info(image_path: str) -> ExtractionResult:
    """
    이미지 파일을 받아 약 정보를 추출합니다.

    Args:
        image_path: 이미지 파일 경로 (jpg, png 등)

    Returns:
        ExtractionResult 객체
    """

    # ── 파일 존재 확인 ──
    path = Path(image_path)
    if not path.exists():
        return ExtractionResult(
            document_type=DocumentType.PILL_ENVELOPE,
            error_message=f"❌ 파일을 찾을 수 없습니다: {image_path}"
        )

    # ── 이미지 읽기 ──
    with open(path, "rb") as f:
        image_bytes = f.read()

    # 확장자로 MIME 타입 결정
    suffix = path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    mime_type = mime_map.get(suffix, "image/jpeg")

    # ── API 호출 (모델 폴백 포함) ──
    client = _get_client()
    last_error = None

    for model_name in MODELS:
        try:
            print(f"🔄 모델 시도 중: {model_name}")

            response = client.models.generate_content(
                model=model_name,
                contents=[
                    types.Content(parts=[
                        types.Part(text=SYSTEM_PROMPT),
                        types.Part(
                            inline_data=types.Blob(
                                mime_type=mime_type,
                                data=image_bytes,
                            )
                        ),
                    ])
                ],
            )

            raw_text = response.text
            print(f"✅ 성공! 사용 모델: {model_name}")

            # ── JSON 파싱 ──
            result = _parse_response(raw_text)
            return result

        except Exception as e:
            error_str = str(e)
            print(f"⚠️  {model_name} 실패: {error_str}")
            last_error = error_str

            # 503이면 잠깐 대기 후 다음 모델 시도
            if "503" in error_str or "UNAVAILABLE" in error_str:
                print("   ⏳ 3초 대기 후 다음 모델 시도...")
                time.sleep(3)
                continue

            # JSON 파싱 오류면 error_message에 담아서 반환
            if "json" in error_str.lower() or "JSONDecodeError" in error_str:
                return ExtractionResult(
                    document_type=DocumentType.PILL_ENVELOPE,
                    error_message=f"JSON 파싱 실패: {error_str}"
                )

            # 그 외 오류도 다음 모델 시도
            continue

    # 모든 모델 실패
    return ExtractionResult(
        document_type=DocumentType.PILL_ENVELOPE,
        error_message=f"❌ 모든 모델 실패. 마지막 오류: {last_error}"
    )