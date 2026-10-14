"""반복 조제 기록 진단 테스트 (읽기 전용, 가상 데이터)."""
import copy

import openpyxl

from backend.services.hira.tests.make_fixtures import COMMON_HEADERS
from backend.services.normalization.adapter import to_common_results
from backend.services.normalization.repeat_report import find_repeat_groups
from backend.services.normalization.service import normalize_hira_file

FAMILY = "00000000-0000-4000-8000-000000000001"
H = ["가나다의원", "라마바약국"]
TYLE = ["타이레놀정500밀리그램", "해열진통소염제", "아세트아미노펜", "000123456", "정", 1, 3, 5]


def _common(tmp_path, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(COMMON_HEADERS)
    for r in rows:
        ws.append(r)
    p = tmp_path / "t.xlsx"
    wb.save(p)
    return to_common_results(normalize_hira_file(p), FAMILY)


def test_repeated_product_is_reported_with_all_dates(tmp_path):
    res = _common(tmp_path, [[1, "2024-05-05", *H, *TYLE], [2, "2024-06-05", *H, *TYLE],
                             [3, "2024-06-05", *H, "없는약정", None, None, "999999999", "정", 1, 1, 1]])
    groups = find_repeat_groups(res)
    assert len(groups) == 1
    g = groups[0]
    assert g["key_type"] == "mfds_product_id" and g["count"] == 2
    assert g["dispensing_dates"] == ["2024-05-05", "2024-06-05"]
    assert len(set(g["source_record_ids"])) == 2


def test_input_is_not_modified_and_nothing_removed(tmp_path):
    res = _common(tmp_path, [[1, "2024-05-05", *H, *TYLE], [2, "2024-06-05", *H, *TYLE]])
    before = copy.deepcopy(res)
    find_repeat_groups(res)
    assert res == before and len(res) == 2


def test_unmatched_repeats_group_by_drug_code(tmp_path):
    row = ["없는약정", None, None, "999999999", "정", 1, 1, 1]
    res = _common(tmp_path, [[1, "2024-05-05", *H, *row], [2, "2024-06-05", *H, *row]])
    g = find_repeat_groups(res)
    assert len(g) == 1 and g[0]["key_type"] == "drug_code" and g[0]["key"] == "999999999"


def test_failed_and_unidentifiable_records_are_skipped(tmp_path):
    res = _common(tmp_path, [
        [1, "2024-05-05", *H, None, None, None, "123", "정", 1, 1, 1],       # FAILED (제품명 없음)
        [2, "2024-05-05", *H, "무명약", None, None, None, "정", 1, 1, 1],    # 코드·성분 없음 → 키 없음
        [3, "2024-06-05", *H, "무명약", None, None, None, "정", 1, 1, 1],
    ])
    assert find_repeat_groups(res) == []  # 이름만으로 같은 약이라고 묶지 않는다


def test_no_repeats_returns_empty(tmp_path):
    assert find_repeat_groups(_common(tmp_path, [[1, "2024-05-05", *H, *TYLE]])) == []
