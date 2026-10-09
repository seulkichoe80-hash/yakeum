"""실제 공공데이터포털 식약처 API 구현체 (2주차에 구현).

API 키는 환경변수 MFDS_API_KEY 로만 읽는다 (코드/커밋에 쓰지 않는다).
응답 형식 확정 전이므로 지금은 인터페이스만 맞춘 스텁이다.
"""
import os
from typing import List

from backend.services.mfds.client import MfdsClient
from backend.services.mfds.models import OfficialItem


class RealMfdsClient(MfdsClient):
    def __init__(self, api_key: str = "", timeout: float = 5.0, retries: int = 3):
        self.api_key = api_key or os.environ.get("MFDS_API_KEY", "")
        self.timeout = timeout
        self.retries = retries
        self.last_warnings: List[str] = []

    def find_by_code(self, code: str) -> List[OfficialItem]:
        raise NotImplementedError("2주차: 실제 API 연동 예정")

    def search_by_name(self, name: str, limit: int = 50) -> List[OfficialItem]:
        raise NotImplementedError("2주차: 실제 API 연동 예정")
