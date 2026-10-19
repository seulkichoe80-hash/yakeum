"""D 전달용 재현 사례 입력(cases.json)이 B 파이프라인 결과와 일치하는지 점검한다 (D 코드는 사용하지 않음)."""
import json
from pathlib import Path

from backend.services.normalization.adapter import validate_common_result
from backend.services.normalization.d_repro import build_cases
from backend.services.normalization.repeat_report import find_repeat_groups

STORED = Path(build_cases.__file__).parent / "cases.json"


def test_stored_cases_match_regenerated_output():
    stored = json.loads(STORED.read_text(encoding="utf-8"))
    regenerated = json.loads(json.dumps({"family_member_id": build_cases.FAMILY, "cases": build_cases.build()}, ensure_ascii=False))
    assert stored == regenerated  # B 코드가 바뀌어 사례가 낡으면 여기서 알 수 있다


def test_all_case_results_pass_contract_validation():
    for case in build_cases.build():
        for r in case["previous"] + case["current"]:
            assert validate_common_result(r) == []


def test_repeat_cases_actually_contain_repeated_products_and_no_row_is_dropped():
    cases = {c["id"]: c for c in build_cases.build()}
    assert len(cases["R1"]["current"]) == 2 and len(find_repeat_groups(cases["R1"]["current"])) == 1
    assert all(len(find_repeat_groups(cases["R2"][side])) == 1 for side in ("previous", "current"))


def test_unknown_strength_cases_have_null_strength_and_empty_or_unnamed_strength():
    cases = {c["id"]: c for c in build_cases.build()}
    r3 = cases["R3"]["current"][0]
    assert r3["status"] == "UNMATCHED" and r3["record"]["ingredients"] == []
    r4 = cases["R4"]["current"][0]
    assert all(i["product_strength"] is None for i in r4["record"]["ingredients"])
