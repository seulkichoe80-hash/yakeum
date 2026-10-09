from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

Number = Decimal


@dataclass
class OfficialIngredient:
    name: str
    amount: Optional[Number] = None
    unit: Optional[str] = None
    ingredient_id: Optional[str] = None  # 공식 응답에 있을 때만


@dataclass
class OfficialItem:
    source: str  # MFDS_DRUG | MFDS_HEALTH_FOOD
    official_id: str  # 품목기준코드 등 (String, 앞자리 0 보존)
    name: str
    ingredients: List[OfficialIngredient] = field(default_factory=list)
    form: Optional[str] = None
    # HIRA 약품코드(보험코드)와 매칭할 수 있는 공식 코드. official_id(품목기준코드 등)와 다른 체계이므로 분리한다.
    insurance_code: Optional[str] = None
