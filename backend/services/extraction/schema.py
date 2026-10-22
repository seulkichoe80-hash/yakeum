# schema.py
# 약이음 Task A - 데이터 구조 정의

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

# ─────────────────────────────────────
# 1. 문서 종류
# ─────────────────────────────────────
class DocumentType(Enum):
    PRESCRIPTION = "처방전"        # 병원 처방전
    PILL_ENVELOPE = "약봉투"       # 약국 약봉투
    HEALTH_SUPPLEMENT = "건강기능식품"  # 영양제 등

# ─────────────────────────────────────
# 2. 복용 시점
# ─────────────────────────────────────
class MealTiming(Enum):
    BEFORE_MEAL = "식전"
    AFTER_MEAL = "식후"
    WITH_MEAL = "식중"
    REGARDLESS = "식사무관"
    BEDTIME = "취침전"
    UNKNOWN = "알수없음"

# ─────────────────────────────────────
# 3. 약 하나의 정보
# ─────────────────────────────────────
@dataclass
class MedicationItem:
    name: str                          # 약 이름 (필수)
    dosage: Optional[str] = None       # 용량 (예: "500mg")
    frequency: Optional[str] = None    # 하루 몇 번 (예: "하루 3회")
    duration: Optional[str] = None     # 복용 기간 (예: "7일")
    timing: MealTiming = MealTiming.UNKNOWN  # 식전/식후
    instructions: Optional[str] = None # 특이사항 (예: "물과 함께")
    confidence: float = -1.0            # AI 확신도 (0.0 ~ 1.0)

# ─────────────────────────────────────
# 4. 이미지 1장에서 추출한 전체 결과
# ─────────────────────────────────────
@dataclass
class ExtractionResult:
    document_type: DocumentType                    # 문서 종류
    medications: List[MedicationItem] = field(default_factory=list)  # 약 목록
    patient_name: Optional[str] = None             # 환자 이름
    hospital_name: Optional[str] = None            # 병원/약국 이름
    prescription_date: Optional[str] = None        # 처방 날짜
    raw_text: Optional[str] = None                 # AI가 읽은 원본 텍스트
    overall_confidence: float = -1.0                # 전체 확신도
    error_message: Optional[str] = None            # 오류 메시지