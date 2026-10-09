from dataclasses import dataclass, field
from typing import List, Optional, Union

Number = Union[int, float]


@dataclass
class OfficialIngredient:
    name: str
    amount: Optional[Number] = None
    unit: Optional[str] = None


@dataclass
class OfficialItem:
    source: str  # MFDS_DRUG | MFDS_HEALTH_FOOD
    official_id: str  # 품목기준코드 등 (String, 앞자리 0 보존)
    name: str
    ingredients: List[OfficialIngredient] = field(default_factory=list)
    form: Optional[str] = None
