# 임시: DATA_SCHEMA.md 확정 시 맞출 것
# 모든 공용 모델은 이 파일 한 곳에만 정의한다. 팀장이 스키마를 합칠 때 이 파일만 고치면 된다.
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Union

Number = Union[int, float]

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
    amount: Optional[Number] = None  # 0 은 "함량 0", None 은 "정보 없음"
    unit: Optional[str] = None
    amount_raw: Optional[str] = None
    source: str = "HIRA"  # HIRA | MFDS (어디서 채워졌는지)


@dataclass
class Dosage:
    dose_per_time: Optional[Number] = None  # 1회 투약량
    times_per_day: Optional[Number] = None  # 1일 투여횟수
    total_days: Optional[int] = None  # 총 투약일수
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
    institution: Optional[str] = None
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
        return asdict(self)


@dataclass
class ParsedRow:
    """HIRA 파서 출력 1행. record 는 해석 실패 시에도 raw_row 를 담아 둔다."""

    record: MedicationRecord
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
