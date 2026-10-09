import json
from pathlib import Path
from typing import List, Optional

from backend.services.mfds.client import MfdsClient
from backend.services.mfds.models import OfficialIngredient, OfficialItem

DEFAULT_DATA = Path(__file__).parent / "data" / "mock_items.json"


class MockMfdsClient(MfdsClient):
    """로컬 샘플 JSON 으로 동작하는 1주차용 구현체 (네트워크 없음)."""

    def __init__(self, data_path: Optional[Path] = None, items: Optional[List[OfficialItem]] = None):
        self.last_warnings: List[str] = []
        self.last_failed = False
        if items is not None:
            self._items = list(items)
            return
        raw = json.loads(Path(data_path or DEFAULT_DATA).read_text(encoding="utf-8"))
        self._items = [
            OfficialItem(
                source=r["source"],
                official_id=str(r["official_id"]),
                name=r["name"],
                form=r.get("form"),
                ingredients=[OfficialIngredient(**i) for i in r.get("ingredients", [])],
            )
            for r in raw
        ]

    def find_by_code(self, code: str) -> List[OfficialItem]:
        self.last_warnings = []
        return [i for i in self._items if i.official_id == code]

    def search_by_name(self, name: str, limit: int = 50) -> List[OfficialItem]:
        self.last_warnings = []
        return self._items[:limit]  # Mock 은 전체를 후보로 반환, 판정은 matcher 가 한다
