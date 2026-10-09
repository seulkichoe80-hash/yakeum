from abc import ABC, abstractmethod
from typing import List, Optional

from backend.services.mfds.models import OfficialItem


class MfdsClient(ABC):
    """식약처 공식 데이터 조회 인터페이스. Mock/Real 구현체를 교체해 쓴다."""

    #: 조회 중 발생한 경고(재시도/타임아웃 등). 서비스가 읽어 warnings 에 옮긴다.
    last_warnings: List[str]

    @abstractmethod
    def find_by_code(self, code: str) -> List[OfficialItem]:
        """품목기준코드/보험코드 정확 일치 항목."""

    @abstractmethod
    def search_by_name(self, name: str, limit: int = 50) -> List[OfficialItem]:
        """이름 후보 조회. 정규화/유사도 판정은 호출자(matcher)가 한다."""
