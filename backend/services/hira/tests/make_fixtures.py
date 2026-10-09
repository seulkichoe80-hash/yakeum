"""가짜 HIRA 샘플 Excel 생성기 (개인정보 없는 더미 데이터)."""
from datetime import datetime

import openpyxl


def make_sample_xlsx(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "진료내역"
    ws["A1"] = "건강보험심사평가원 진료내역(더미)"
    ws.merge_cells("A1:I1")
    ws["A3"] = "조회기간: 2024-01-01 ~ 2024-12-31"
    headers = ["진료일자", "요양기관명", "약품명", "약품코드", "성분명", "함량", "1회 투약량", "1일 투여횟수", "총 투약일수"]
    for c, h in enumerate(headers, 1):
        ws.cell(5, c, h)
    rows = [
        # 정상 행
        [datetime(2024, 3, 5), "가나다의원", "타이레놀정500밀리그램", "000123456", "아세트아미노펜", "500mg", 1, 3, 5],
        # 문자열 날짜 + 앞자리 0 코드 + 복용량 0
        ["2024.03.07", "가나다의원", "뮤코펙트정 30mg", "198800001", None, None, 0, 3, 3],
        # 빈 행
        [None] * 9,
        # 이상 날짜 + 중복 후보(캡슐/정 동명)
        ["2024-13-45", "라마바약국", "가나릴", None, None, None, 1, 2, 7],
        # 매칭 실패
        ["20240401", "라마바약국", "없는약정", "999999999", None, None, None, None, None],
        # 약품명 없음 → FAILED
        ["2024-04-02", "라마바약국", None, "123", None, None, 1, 1, 1],
    ]
    for r, row in enumerate(rows, 6):
        for c, v in enumerate(row, 1):
            if v is not None:
                ws.cell(r, c, v)
    wb.save(path)
    return path
