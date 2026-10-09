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


COMMON_HEADERS = ["번호", "조제일자", "처방기관", "조제기관", "제품명", "약효분류", "성분명", "약품코드",
                  "단위", "1회 투약량", "1일 투여횟수", "총 투약일수"]


def make_common_sample_xlsx(path):
    """공통 규격 변환 검증용 가상 샘플 (DATA_SCHEMA 가 나열한 HIRA 원본 필드 순서, 개인정보 없음)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "투약이력"
    ws["A1"] = "내가 먹는 약! 한눈에 (가상 더미)"
    for c, h in enumerate(COMMON_HEADERS, 1):
        ws.cell(3, c, h)
    rows = [
        [1, datetime(2024, 3, 5), "가나다의원", "라마바약국", "타이레놀정500밀리그램", "해열진통소염제", "아세트아미노펜", "000123456", "정", 1, 3, 5],
        [2, "2024-03-05", "가나다의원", "라마바약국", "가나릴", "가상분류", "가짜성분", None, "정", "1/2", 2, 7],  # 후보 복수
        [3, "2024-03-05", "가나다의원", "라마바약국", "가나릴", "가상분류", "가짜성분", None, "정", "1/2", 2, 7],  # 동일 내용 반복
        [4, "20240401", "마바사의원", "라마바약국", "없는약정", None, None, "999999999", "캡슐", 0, 2, 3],  # 매칭 실패, 0 구분
        [5, "2024-13-45", "마바사의원", "라마바약국", "뮤코펙트정 30mg", None, None, "198800001", "정", 1, 1, 1],  # 이상 날짜
        [6, "2024-04-02", "마바사의원", "라마바약국", None, None, None, "123", "정", 1, 1, 1],  # 제품명 없음
    ]
    for r, row in enumerate(rows, 4):
        for c, v in enumerate(row, 1):
            if v is not None:
                ws.cell(r, c, v)
    wb.save(path)
    return path
