# B 내부 모델 (파싱·매칭 작업용). 팀 공통 규격(docs/DATA_SCHEMA.md MedicationRecord)과는 다르다.
# 공통 규격으로의 변환은 normalization/adapter.py 가 전담한다 (B 내부 → 약이음 공통 데이터).
# 수량은 float 를 쓰지 않고 Decimal 로 보존한다.
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional

Number = Decimal

STATUS_MATCHED = "MATCHED"
STATUS_PARTIAL = "PARTIAL"
STATUS_UNMATCHED = "UNMATCHED"
STATUS_FAILED = "FAILED"


@dataclass
class TextField:
    """원본(raw)과 정규화(normalized)를 분리 보존. 모르면 None."""

    raw: Optional[str] = None
    normalized: Optional[str] = None


@dataclass
class Ingredient:
    name: TextField = field(default_factory=TextField)
    amount: Optional[Number] = None  # 0 은 "함량 0", None 은 "정보 없음" (Decimal)
    unit: Optional[str] = None
    amount_raw: Optional[str] = None
    source: str = "HIRA"  # HIRA | MFDS (어디서 채워졌는지)
    official_id: Optional[str] = None  # 공식 응답에서 확인된 성분 식별자만 (추측 금지)


@dataclass
class Dosage:
    dose_per_time: Optional[Number] = None  # 1회 투약량
    times_per_day: Optional[Number] = None  # 1일 투여횟수
    total_days: Optional[Number] = None  # 총 투약일수 (정수값이어도 Decimal)
    raw: Dict[str, Optional[str]] = field(default_factory=dict)


@dataclass
class MedicationRecord:
    source: str = "HIRA"
    date: Optional[str] = None  # YYYY-MM-DD
    date_raw: Optional[str] = None
    drug_code: Optional[str] = None  # 항상 String (앞자리 0 보존)
    product_name: TextField = field(default_factory=TextField)
    ingredients: List[Ingredient] = field(default_factory=list)
    dosage: Dosage = field(default_factory=Dosage)
    institution: Optional[str] = None  # 처방/조제 구분이 불명확한 단일 기관 컬럼 (공통 규격으로는 매핑하지 않음)
    row_no: Optional[str] = None  # 원본 '번호'
    dispensing_date: Optional[str] = None  # 조제일자 (YYYY-MM-DD)
    dispensing_date_raw: Optional[str] = None
    prescribing_institution: Optional[str] = None
    dispensing_institution: Optional[str] = None
    drug_category: Optional[str] = None  # 약효분류
    unit: Optional[str] = None  # 1회 투약량 단위
    official_name: Optional[str] = None  # 공식 데이터에 단일 매칭된 제품명
    source_ref: Dict[str, Any] = field(default_factory=dict)  # file/sheet/row
    raw_row: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MatchInfo:
    source: Optional[str] = None  # MFDS_DRUG | MFDS_HEALTH_FOOD | None
    official_id: Optional[str] = None
    match_method: str = "NONE"  # CODE_EXACT | NAME_EXACT | NAME_FUZZY | NONE


@dataclass
class NormalizationResult:
    status: str
    record: MedicationRecord
    match: MatchInfo = field(default_factory=MatchInfo)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class ParsedRow:
    """HIRA 파서 출력 1행. record 는 해석 실패 시에도 raw_row 를 담아 둔다."""

    record: MedicationRecord
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def decimal_to_str(d: Decimal) -> str:
    """Decimal 을 지수 표기 없이 정밀도를 보존한 문자열로 (1.0 → "1", 0.50 → "0.5")."""
    if d == d.to_integral_value():
        return str(int(d))
    return format(d.normalize(), "f")


def _jsonable(o: Any) -> Any:
    if isinstance(o, Decimal):
        return decimal_to_str(o)
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_jsonable(v) for v in o]
    return o
