import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

print("파이썬 파일이 정상적으로 실행되었습니다!")

# schema.py와 prompt.py 로드
try:
    from schema import (
        DocumentType, MealTiming,
        MedicationItem, ExtractionResult
    )
    from prompt import SYSTEM_PROMPT
except ImportError:
    import sys
    sys.path.append(os.path.dirname(__file__))
    from schema import DocumentType, MealTiming, MedicationItem, ExtractionResult
    from prompt import SYSTEM_PROMPT

# 환경 변수 로드
load_dotenv()

# ✅ check_models.py에서 확인된 '사용 가능한' 모델들로 교체합니다.
MODELS = [
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "gemini-3.8-flash"
]

def _get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("❌ .env 파일에 GEMINI_API_KEY가 없습니다!")
    return genai.Client(api_key=api_key)

def _parse_response(raw_json: str) -> ExtractionResult:
    cleaned = raw_json.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json")[1].split("```")[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```")[1].split("```")[0].strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return ExtractionResult(document_type=DocumentType.PILL_ENVELOPE, error_message="JSON 파싱 실패")

    doc_type_map = {
        "처방전": DocumentType.PRESCRIPTION,
        "약봉투": DocumentType.PILL_ENVELOPE,
        "건강기능식품": DocumentType.HEALTH_SUPPLEMENT,
    }
    document_type = doc_type_map.get(data.get("document_type", ""), DocumentType.PILL_ENVELOPE)

    timing_map = {
        "식전": MealTiming.BEFORE_MEAL, "식후": MealTiming.AFTER_MEAL,
        "식중": MealTiming.WITH_MEAL, "식사무관": MealTiming.REGARDLESS,
        "취침전": MealTiming.BEDTIME, "알수없음": MealTiming.UNKNOWN,
    }

    medications = []
    for item in data.get("medications", []):
        timing = timing_map.get(item.get("timing", "알수없음"), MealTiming.UNKNOWN)
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

def extract_medicine_info(image_path: str) -> ExtractionResult:
    path = Path(image_path)
    if not path.exists():
        return ExtractionResult(document_type=DocumentType.PILL_ENVELOPE, error_message=f"❌ 파일을 찾을 수 없습니다: {image_path}")

    with open(path, "rb") as f:
        image_bytes = f.read()

    suffix = path.suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime_type = mime_map.get(suffix, "image/jpeg")

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
                        types.Part(inline_data=types.Blob(mime_type=mime_type, data=image_bytes)),
                    ])
                ],
            )
            print(f"✅ 성공! 사용 모델: {model_name}")
            return _parse_response(response.text)
        except Exception as e:
            last_error = str(e)
            print(f"⚠️  {model_name} 실패: {last_error}")
            time.sleep(1)

    return ExtractionResult(document_type=DocumentType.PILL_ENVELOPE, error_message=f"모든 모델 실패: {last_error}")

# ✅ 이 부분이 있어야 실제로 실행이 됩니다!
if __name__ == "__main__":
    # test_image.jpg 파일이 task-a 폴더 안에 있는지 확인하세요.
    # 만약 상위 폴더에 있다면 "../test_image.jpg"로 수정하세요.
    test_img = "test_image.jpg" 
    
    print(f"🔍 이미지 분석 시작: {test_img}")
    result = extract_medicine_info(test_img)
    
    print("\n" + "="*30)
    if result.error_message:
        print(f"❌ 오류 발생: {result.error_message}")
    else:
        print(f"📄 문서 종류: {result.document_type.value}")
        print(f"👤 환자 이름: {result.patient_name}")
        print(f"💊 추출된 약 개수: {len(result.medications)}개")
        for i, med in enumerate(result.medications, 1):
            print(f"  {i}. {med.name} ({med.timing.value})")
    print("="*30)