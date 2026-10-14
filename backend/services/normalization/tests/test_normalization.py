import json
from pathlib import Path

from backend.services.hira.tests.make_fixtures import make_sample_xlsx
from backend.services.mfds.mock_client import MockMfdsClient
from backend.services.normalization.matcher import match
from backend.services.normalization.name_normalizer import normalize_name
from backend.services.normalization.service import normalize_hira_file

EXPECTED = Path(__file__).parent / "expected_sample.json"


def _run(tmp_path):
    return normalize_hira_file(make_sample_xlsx(tmp_path / "sample_hira.xlsx"))


def test_sample_excel_matches_expected_json(tmp_path):
    actual = [r.to_dict() for r in _run(tmp_path)]
    assert actual == json.loads(EXPECTED.read_text(encoding="utf-8"))


def test_statuses(tmp_path):
    assert [r.status for r in _run(tmp_path)] == ["MATCHED", "MATCHED", "PARTIAL", "UNMATCHED", "FAILED"]


def test_code_exact_and_ingredients_filled_from_mfds(tmp_path):
    r = _run(tmp_path)[1]
    assert r.match.match_method == "CODE_EXACT" and r.match.official_id == "OFFICIAL-0002"
    assert r.record.ingredients[0].source == "MFDS"


def test_duplicate_candidates_are_partial(tmp_path):
    r = _run(tmp_path)[2]
    assert r.status == "PARTIAL" and r.match.official_id is None
    assert r.match.match_method == "NAME_EXACT"


def test_unmatched_keeps_raw(tmp_path):
    r = _run(tmp_path)[3]
    assert r.match.match_method == "NONE" and r.record.product_name.raw == "없는약정"


def test_normalize_name():
    assert normalize_name("타이레놀정 500mg (10정)") == "타이레놀"
    assert normalize_name(None) is None


def test_fuzzy_match_threshold():
    c = MockMfdsClient()
    out = match(c, None, "뮤코펙토정", 0.7)
    assert out.method == "NAME_FUZZY" and out.candidates[0].official_id == "OFFICIAL-0002"
    assert match(c, None, "뮤코펙토정", 0.99).method == "NONE"
