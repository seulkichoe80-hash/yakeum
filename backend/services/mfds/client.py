from abc import ABC, abstractmethod
from typing import List

from backend.services.mfds.models import OfficialItem


class MfdsClient(ABC):
    """식약처 공식 데이터 조회 인터페이스. Mock/Real 구현체를 교체해 쓴다."""

    #: 직전 호출에서 발생한 경고(재시도 소진/타임아웃 등). 서비스가 warnings 에 옮긴다.
    last_warnings: List[str] = []
    #: 직전 호출에서 조회 자체가 실패했는지 ("없음"과 "조회 실패"를 구분하기 위함).
    last_failed: bool = False

    @abstractmethod
    def find_by_code(self, code: str) -> List[OfficialItem]:
        """품목기준코드/보험코드 정확 일치 항목."""

    @abstractmethod
    def search_by_name(self, name: str, limit: int = 50) -> List[OfficialItem]:
        """이름 후보 조회. 정규화/유사도 판정은 호출자(matcher)가 한다."""
