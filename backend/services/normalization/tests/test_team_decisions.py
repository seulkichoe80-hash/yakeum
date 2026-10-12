"""B→D 연동 협의 결정(PoC 방향) 회귀 테스트. 가상 데이터·Mock 만 사용, 외부 API 호출 없음.

검증하는 방향:
 1 원본 조제일 보존 / 2 반복 조제행 자동 삭제·축약 금지 / 3 status·match·warnings·errors 보존
 4 user_confirmed=false 유지 / 5 원본 제품명 보존 / 6 product_strength null 유지
 7 빈 성분 원본 보존, 성분만으로 매칭 확정 금지 / 9 ID(UUID5/해시) 안정성
"""
import uuid
from decimal import Decimal
from pathlib import Path

import openpyxl

from backend.services.hira.tests.make_fixtures import COMMON_HEADERS
from backend.services.mfds.mock_client import MockMfdsClient
from backend.services.mfds.models import OfficialIngredient, OfficialItem
from backend.services.normalization.adapter import to_common_results, validate_common_result
from backend.services.normalization.service import normalize_hira_file

FAMILY = "00000000-0000-4000-8000-000000000001"
OTHER_FAMILY = "00000000-0000-4000-8000-000000000002"
TYLE = ["타이레놀정500밀리그램", "해열진통소염제", "아세트아미노펜", "000123456", "정", 1, 3, 5]  # 제품명~총투약일수


def _xlsx(tmp_path: Path, rows, name="t.xlsx") -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(COMMON_HEADERS)
    for r in rows:
        ws.append(r)
    p = tmp_path / name
    wb.save(p)
    return p


def _row(no, date, product=TYLE, presc="가나다의원", disp="라마바약국"):
    return [no, date, presc, disp, *product]


def _run(path, client=None, family=FAMILY):
    internal = normalize_hira_file(path, client=client)
    return internal, to_common_results(internal, family)


# ---- 1·2 조제일 보존, 반복행 보존 ------------------------------------------------------------
def test_every_dispensing_date_is_preserved_and_nothing_is_collapsed(tmp_path):
    p = _xlsx(tmp_path, [_row(1, "2024-01-10"), _row(2, "2024-02-10"), _row(3, "2024-03-10")])
    _, res = _run(p)
    recs = [r["record"] for r in res]
    assert [x["dispensing_date"] for x in recs] == ["2024-01-10", "2024-02-10", "2024-03-10"]
    assert [x["record_date"] for x in recs] == ["2024-01-10", "2024-02-10", "2024-03-10"]
    assert len({x["record_id"] for x in recs}) == 3  # 같은 약이어도 조제일마다 별도 record


def test_identical_repeated_rows_are_kept_with_duplicate_warning(tmp_path):
    p = _xlsx(tmp_path, [_row(1, "2024-01-10"), _row(2, "2024-01-10"), _row(3, "2024-01-10")])
    internal, res = _run(p)
    assert len(res) == 3 and all(r["record"] for r in res)  # 삭제·축약 없음
    assert len({r["record"]["record_id"] for r in res}) == 3
    assert not any("중복" in w["message"] for w in res[0]["warnings"])
    assert any("중복 행" in w["message"] for w in res[1]["warnings"])
    assert any("중복 행" in w["message"] for w in res[2]["warnings"])


# ---- 3 상태·매칭·경고·오류 보존 --------------------------------------------------------------
def test_status_match_warnings_errors_are_carried_over(tmp_path):
    p = _xlsx(tmp_path, [
        _row(1, "2024-03-05"),                                                   # MATCHED
        _row(2, "2024-03-05", ["가나릴", "가상", "가짜성분", None, "정", 1, 2, 7]),  # PARTIAL (후보 복수)
        _row(3, "2024-03-05", ["없는약정", None, None, "999999999", "정", 0, 2, 3]),  # UNMATCHED
        _row(4, "2024-03-05", [None, None, None, "123", "정", 1, 1, 1]),           # FAILED
    ])
    internal, res = _run(p)
    assert [r["status"] for r in res] == [i.status for i in internal] == ["MATCHED", "PARTIAL", "UNMATCHED", "FAILED"]
    for i, r in zip(internal, res):
        assert [w["message"] for w in r["warnings"]] == i.warnings  # 경고 문구 보존
        if r["status"] == "FAILED":
            assert {e["message"] for e in r["errors"]} >= set(i.errors)  # 내부 오류는 모두 남음
        else:
            assert r["errors"] == []
        assert r["match"]["official_id"] == i.match.official_id
        assert validate_common_result(r) == []
    assert res[3]["record"] is None and res[3]["errors"]
    assert res[2]["match"] == {"source": None, "official_id": None, "match_method": None}
    assert res[2]["record"]["product_name_raw"] == "없는약정"


# ---- 4 user_confirmed ------------------------------------------------------------------------
def test_user_confirmed_false_and_confidence_null_for_all_hira_records(tmp_path):
    p = _xlsx(tmp_path, [_row(1, "2024-01-10"), _row(2, "2024-02-10", ["없는약정", None, None, None, "정", 1, 1, 1])])
    _, res = _run(p)
    assert all(r["record"]["user_confirmed"] is False and r["record"]["confidence"] is None for r in res)


# ---- 5 제품명 구분 ---------------------------------------------------------------------------
def test_raw_product_name_is_never_overwritten(tmp_path):
    raw = "타이레놀정500밀리그램 "  # 끝 공백까지 포함해 raw 는 공백 제거 외에는 건드리지 않는다
    p = _xlsx(tmp_path, [_row(1, "2024-01-10", [raw, *TYLE[1:]])])
    internal, res = _run(p)
    rec = res[0]["record"]
    assert rec["product_name_raw"] == raw.strip()
    assert internal[0].record.product_name.raw == raw.strip()
    assert internal[0].record.official_name == "타이레놀정500밀리그램"  # 공식명은 별도 보관


def test_unmatched_has_only_rule_normalized_name_not_official(tmp_path):
    p = _xlsx(tmp_path, [_row(1, "2024-01-10", ["없는약정", None, None, None, "정", 1, 1, 1])])
    internal, res = _run(p)
    assert internal[0].record.official_name is None
    assert res[0]["record"]["product_name_raw"] == "없는약정"
    assert res[0]["record"]["mfds_product_id"] is None


# ---- 6 함량 null 유지 --------------------------------------------------------------------------
def test_product_strength_stays_null_when_unknown(tmp_path):
    item = OfficialItem("MFDS_DRUG", "OFF-1", "타이레놀정500밀리그램", [OfficialIngredient("아세트아미노펜", Decimal("500"), "mg")], None, "000123456")
    p = _xlsx(tmp_path, [_row(1, "2024-01-10")])
    _, res = _run(p, MockMfdsClient(items=[item]))
    ing = res[0]["record"]["ingredients"][0]
    # HIRA 성분이 있으면 공식 함량으로 덮어쓰거나 합치지 않는다 (불확실한 동등성 확정 금지)
    assert ing["ingredient_name_raw"] == "아세트아미노펜"
    assert ing["product_strength"] is None and ing["product_strength_unit"] is None


def test_null_dose_is_not_converted_to_zero(tmp_path):
    p = _xlsx(tmp_path, [_row(1, "2024-01-10", ["가상정", None, None, None, "정", None, None, None])])
    rec = _run(p)[1][0]["record"]
    assert rec["dose_per_administration"] is None and rec["administrations_per_day"] is None and rec["duration_days"] is None


# ---- 7 빈 성분 -----------------------------------------------------------------------------------
def test_empty_ingredients_are_preserved_as_empty_list(tmp_path):
    p = _xlsx(tmp_path, [_row(1, "2024-01-10", ["없는약정", None, None, "999999999", "정", 1, 1, 1])])
    internal, res = _run(p)
    assert res[0]["record"]["ingredients"] == []
    assert res[0]["status"] == "UNMATCHED"
    assert any("성분" in w["message"] for w in res[0]["warnings"])  # 비어 있음을 경고로 남김


def test_ingredient_name_alone_never_confirms_a_match(tmp_path):
    # 제품명·코드는 다르고 성분만 같은 공식 항목이 있어도 매칭을 확정하지 않는다
    item = OfficialItem("MFDS_DRUG", "OFF-9", "전혀다른제품정", [OfficialIngredient("아세트아미노펜", None, None)], None, "777")
    p = _xlsx(tmp_path, [_row(1, "2024-01-10", ["내가모르는약정", None, "아세트아미노펜", "123456", "정", 1, 1, 1])])
    _, res = _run(p, MockMfdsClient(items=[item]))
    assert res[0]["status"] == "UNMATCHED" and res[0]["record"]["mfds_product_id"] is None


# ---- 9 ID 안정성 ------------------------------------------------------------------------------
def _ids(res):
    return [(r["record"]["source_record_id"], r["record"]["record_id"]) for r in res if r["record"]]


def test_reupload_same_content_gives_same_ids_regardless_of_path_and_metadata(tmp_path):
    rows = [_row(1, "2024-01-10"), _row(2, "2024-02-10")]
    a = _ids(_run(_xlsx(tmp_path, rows, "a.xlsx"))[1])
    # 번호 컬럼과 파일명, 날짜 셀 서식(문자열/날짜형)이 달라도 동일해야 함
    import datetime
    rows_b = [_row(11, datetime.datetime(2024, 1, 10)), _row(12, datetime.datetime(2024, 2, 10))]
    b = _ids(_run(_xlsx(tmp_path, rows_b, "b_다른이름.xlsx"))[1])
    assert a == b


def test_row_order_change_does_not_change_ids(tmp_path):
    rows = [_row(1, "2024-01-10"), _row(2, "2024-02-10", ["뮤코펙트정 30mg", "가상", "암브록솔", "198800001", "정", 1, 3, 3]),
            _row(3, "2024-03-10", ["없는약정", None, None, "999999999", "정", 1, 2, 3])]
    fwd = set(_ids(_run(_xlsx(tmp_path, rows, "f.xlsx"))[1]))
    rev = set(_ids(_run(_xlsx(tmp_path, list(reversed(rows)), "r.xlsx"))[1]))
    assert fwd == rev and len(fwd) == 3


def test_same_product_different_date_or_institution_get_different_ids(tmp_path):
    rows = [_row(1, "2024-01-10"), _row(2, "2024-02-10"), _row(3, "2024-01-10", disp="다른약국")]
    ids = [x[0] for x in _ids(_run(_xlsx(tmp_path, rows))[1])]
    assert len(set(ids)) == 3


def test_ids_do_not_depend_on_matching_outcome(tmp_path):
    p = _xlsx(tmp_path, [_row(1, "2024-01-10")])
    with_mfds = _ids(_run(p)[1])
    without = _ids(_run(p, MockMfdsClient(items=[]))[1])  # 공식 데이터가 없어도(미매칭이어도) 같은 ID
    assert with_mfds == without


def test_family_changes_record_id_but_not_source_record_id(tmp_path):
    p = _xlsx(tmp_path, [_row(1, "2024-01-10")])
    internal = normalize_hira_file(p)
    a = to_common_results(internal, FAMILY)[0]["record"]
    b = to_common_results(internal, OTHER_FAMILY)[0]["record"]
    assert a["source_record_id"] == b["source_record_id"]
    assert a["record_id"] != b["record_id"]
    uuid.UUID(a["record_id"]); uuid.UUID(b["record_id"])


def test_duplicate_occurrence_ids_stable_across_reupload(tmp_path):
    rows = [_row(1, "2024-01-10"), _row(2, "2024-01-10")]
    a = _ids(_run(_xlsx(tmp_path, rows, "a.xlsx"))[1])
    b = _ids(_run(_xlsx(tmp_path, rows, "b.xlsx"))[1])
    assert a == b and a[0] != a[1]
