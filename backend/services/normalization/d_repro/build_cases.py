"""D팀 전달용 결함 재현 사례 입력 생성 (가상 Excel → B 파이프라인 → 공통 NormalizationResult).

실행(저장소 루트): python -m backend.services.normalization.d_repro.build_cases
결과: d_repro/cases.json (개인정보 없음, 가상 ID·가상 약품). B 코드만 사용하며 D 코드는 쓰지 않는다.
"""
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import openpyxl

from backend.services.hira.tests.make_fixtures import COMMON_HEADERS
from backend.services.normalization.adapter import to_common_results
from backend.services.normalization.service import normalize_hira_file

FAMILY = "00000000-0000-4000-8000-000000000001"  # 가상
H = ["가나다의원", "라마바약국"]
TYLE = ["타이레놀정500밀리그램", "해열진통소염제", "아세트아미노펜", "000123456", "정"]
UNK = ["없는약정", None, None, "999999999", "정"]
OUT = Path(__file__).parent / "cases.json"


def _results(rows: List[list]) -> List[Dict[str, Any]]:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(COMMON_HEADERS)
    for r in rows:
        ws.append(r)
    p = Path(tempfile.mkdtemp()) / "virtual.xlsx"
    wb.save(p)
    return to_common_results(normalize_hira_file(p), FAMILY)


def build() -> List[Dict[str, Any]]:
    return [
        {"id": "R1", "title": "한 시점에 같은 약이 2줄 (이전 1줄 → 현재 2줄)",
         "expect_by_design": "계속 복용 중인 약이 MAINTAINED 또는 대표 기록 1건 비교",
         "previous": _results([[1, "2024-02-05", *H, *TYLE, 1, 3, 5]]),
         "current": _results([[1, "2024-05-05", *H, *TYLE, 1, 3, 5], [2, "2024-06-05", *H, *TYLE, 1, 3, 5]])},
        {"id": "R2", "title": "양쪽 시점 모두 같은 약이 2줄",
         "expect_by_design": "같은 약의 반복 조제는 같은 약으로 비교",
         "previous": _results([[1, "2024-01-05", *H, *TYLE, 1, 3, 5], [2, "2024-02-05", *H, *TYLE, 1, 3, 5]]),
         "current": _results([[1, "2024-05-05", *H, *TYLE, 1, 3, 5], [2, "2024-06-05", *H, *TYLE, 1, 3, 5]])},
        {"id": "R3", "title": "UNMATCHED + 성분 없음 + 약품코드만 동일 (성분·함량 모두 알 수 없음)",
         "expect_by_design": "성분·함량 동일성을 확인할 수 없으므로 SAME_INGREDIENT_SAME_STRENGTH 로 확정하지 않음",
         "previous": _results([[1, "2024-03-05", *H, *UNK, 1, 2, 3]]),
         "current": _results([[1, "2024-06-10", *H, *UNK, 1, 2, 3]])},
        {"id": "R4", "title": "성분명은 있으나 함량 null (HIRA 에 함량 컬럼 없음) + 투약량 동일",
         "expect_by_design": "함량을 모르면 '같은 함량'이라는 사유를 붙이지 않음",
         "previous": _results([[1, "2024-03-05", *H, *TYLE, 1, 3, 5]]),
         "current": _results([[1, "2024-06-10", *H, *TYLE, 1, 3, 5]])},
    ]


if __name__ == "__main__":
    OUT.write_text(json.dumps({"family_member_id": FAMILY, "cases": build()}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("saved", OUT)
