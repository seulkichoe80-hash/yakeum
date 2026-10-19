"""Offline photo review -> real B/D functions, using only virtual source JSON."""

from copy import deepcopy
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.services.normalization.structured import normalize_structured_record
from backend.services.normalization.adapter import validate_common_result
from backend.services.mfds.mock_client import MockMfdsClient
from backend.services.mfds.models import OfficialItem

FAMILY = "00000000-0000-4000-8000-000000000001"
OTHER = "00000000-0000-4000-8000-000000000002"
client = TestClient(app)


def document(side, scenario="single"):
    return {"document_id": "10000000-0000-4000-8000-00000000000" + ("1" if side == "previous" else "2"),
            "record_date": "2026-09-01" if side == "previous" else "2026-10-19",
            "source_type": "MEDICINE_BAG", "scenario": scenario}


def extract(doc, family=FAMILY):
    response = client.post("/api/local-demo/photos/extract", json={**doc, "family_member_id": family})
    assert response.status_code == 200
    return response.json()["results"]


def draft(record):
    return {"product": record["product_name_raw"] if record else "", "ingredients": [
        {"name": i["ingredient_name_raw"] or "", "strength": i["product_strength"] or "", "unit": i["product_strength_unit"] or "", "originalIndex": n}
        for n, i in enumerate(record["ingredients"] if record else [])],
        "dose": record["dose_per_administration"] or "" if record else "", "doseUnit": record["unit"] or "" if record else "",
        "perDay": record["administrations_per_day"] or "" if record else "", "duration": record["duration_days"] or "" if record else "",
        "directions": record["dosage_text_raw"] or "" if record else ""}


def batch(side, scenario="single"):
    doc = document(side, scenario)
    return {**doc, "reviews": [{"index": n, "confirmed": True, "draft": draft(r["record"])} for n,r in enumerate(extract(doc))]}


def payload(scenario="single", confirmed=False):
    return {"family_member_id": FAMILY, "previous": batch("previous", scenario), "current": batch("current", scenario), "normalization_confirmed": confirmed}


def process(body):
    response = client.post("/api/local-demo/photos/process", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_normal_preview_then_comparison_and_separate_intake():
    body = payload()
    before = deepcopy(body)
    # Assert that none of the demo work can route through a live provider.
    with patch("backend.api.extraction_provider._request_gemini", side_effect=AssertionError("live forbidden")), patch("backend.services.mfds.real_client.RealMfdsClient.search_by_name", side_effect=AssertionError("live forbidden")):
        preview = process(body)
        assert preview["stage"] == "normalized"
        assert preview["reconciliation_result"] is None
        assert preview["normalization_results"]["current"][0]["record"]["user_confirmed"] is False
        result = process({**body, "normalization_confirmed": True})
    assert body == before
    assert result["stage"] == "compared"
    assert result["reconciliation_result"]["items"][0]["status"] == "MAINTAINED"
    assert result["normalization_results"]["current"][0]["record"]["user_confirmed"] is True
    assert result["original_results"]["current"][0]["record"]["user_confirmed"] is False
    assert all(s["intake_status"] == "UNKNOWN" and s["verification_status"] == "PENDING" for s in result["current_intake_states"])


def test_multiple_products_multiple_ingredients_and_decimal_edits():
    body = payload("multiple", True)
    body["current"]["reviews"][1]["draft"]["ingredients"][0]["strength"] = "0.500000000000000000001"
    result = process(body)
    assert result["stage"] == "compared"
    assert len(result["reconciliation_result"]["items"]) == 2
    assert result["reconciliation_result"]["items"][1]["status"] == "DOSE_CHANGED"
    normalized = result["normalization_results"]["current"][1]["record"]
    assert len(normalized["ingredients"]) == 2
    assert normalized["ingredients"][0]["product_strength"] == "0.500000000000000000001"
    assert result["original_results"]["current"][1]["record"]["ingredients"][0]["product_strength"] == "0.5"


@pytest.mark.parametrize("scenario", ["missing", "failed", "unknown", "repeat"])
def test_unresolved_cases_preserve_both_sides_without_fabricated_results(scenario):
    result = process(payload(scenario, True))
    assert result["stage"] == "held"
    assert result["pending_decisions"]
    assert result["reconciliation_result"] is None
    assert result["current_intake_states"] == []
    assert len(result["original_results"]["previous"]) == len(result["original_results"]["current"])
    assert result["normalization_results"]["current"]
    if scenario == "repeat":
        assert len(result["normalization_results"]["current"]) == 2


def test_partial_failure_does_not_infer_missing_from_omitted_records():
    body = payload("multiple", True)
    body["current"]["reviews"].pop()
    result = process(body)
    assert result["stage"] == "held"
    assert result["reconciliation_result"] is None
    assert len(result["original_results"]["current"]) == 2


@pytest.mark.parametrize("change", ["unconfirmed", "duplicate", "invalid-number", "no-name", "conflicting-ingredients", "same-document"])
def test_unsafe_review_requests_are_held(change):
    body = payload(confirmed=True)
    current = body["current"]
    if change == "unconfirmed": current["reviews"][0]["confirmed"] = False
    if change == "duplicate": current["reviews"].append(deepcopy(current["reviews"][0]))
    if change == "invalid-number": current["reviews"][0]["draft"]["dose"] = "1e309"
    if change == "no-name": current["reviews"][0]["draft"]["product"] = ""
    if change == "conflicting-ingredients": current["reviews"][0]["draft"]["ingredients"][0]["name"] = "다른성분"
    if change == "same-document": current["document_id"] = body["previous"]["document_id"]
    result = process(body)
    assert result["stage"] == "held" and result["reconciliation_result"] is None


def test_reprocessing_clears_old_values_and_zero_is_preserved():
    body = payload(confirmed=True)
    assert process(body)["reconciliation_result"]["items"][0]["status"] == "MAINTAINED"
    body["current"]["reviews"][0]["draft"]["dose"] = "0"
    result = process(body)
    assert result["reconciliation_result"]["items"][0]["status"] == "DOSE_CHANGED"
    assert result["normalization_results"]["current"][0]["record"]["dose_per_administration"] == "0"


def test_explicit_complete_snapshot_difference_never_means_stopped():
    for previous_case, current_case, expected in [("multiple", "single", "NEEDS_CONFIRMATION"), ("single", "multiple", "NEW")]:
        body = {"family_member_id": FAMILY, "previous": batch("previous", previous_case),
                "current": batch("current", current_case), "normalization_confirmed": True}
        result = process(body)
        assert result["stage"] == "compared"
        statuses = [item["status"] for item in result["reconciliation_result"]["items"]]
        assert expected in statuses
        assert set(statuses) <= {"MAINTAINED", "NEW", "DOSE_CHANGED", "NEEDS_CONFIRMATION"}
        assert all(state["intake_status"] == "UNKNOWN" for state in result["current_intake_states"])


def test_family_ids_and_request_bounds_rejected_without_echoing_body():
    response = client.post("/api/local-demo/photos/extract", json={**document("current"), "family_member_id": "invalid"})
    assert response.status_code == 422
    # Family scope derives from the request context, not a candidate/AI claim.
    body = payload(confirmed=True); body["family_member_id"] = OTHER
    result = process(body)
    assert result["reconciliation_result"]["family_member_id"] == OTHER
    assert result["original_results"]["current"][0]["record"]["family_member_id"] == OTHER
    oversized = payload(); oversized["current"]["reviews"][0]["draft"]["product"] = "x" * 2001
    assert client.post("/api/local-demo/photos/process", json=oversized).status_code == 422


def test_ids_stable_on_retry_but_new_document_is_not_automatically_deduplicated():
    doc = document("current")
    a = extract(doc); b = extract(doc)
    assert a == b
    other = extract({**doc, "document_id": document("previous")["document_id"]})
    assert a[0]["record"]["record_id"] != other[0]["record"]["record_id"]
    assert a[0]["record"]["record_id"] != extract(doc, OTHER)[0]["record"]["record_id"]


@pytest.mark.parametrize("failure", ["missing-product", "family", "bad-decimal", "bad-ingredient-name", "bad-source-id", "bad-warning", "empty-ingredients", "lookup-failure", "multiple-matches"])
def test_formal_structured_normalization_preserves_input_and_safe_failure(failure):
    source = extract(document("current"))[0]
    if failure == "missing-product": source["record"]["product_name_raw"] = ""
    if failure == "family": source["record"]["family_member_id"] = OTHER
    if failure == "bad-decimal": source["record"]["dose_per_administration"] = "NaN"
    if failure == "bad-ingredient-name": source["record"]["ingredients"][0]["ingredient_name_raw"] = 123
    if failure == "bad-source-id": source["record"]["source_record_id"] = True
    if failure == "bad-warning": source["warnings"] = [{"code": False, "message": "invalid", "field": None}]
    if failure == "empty-ingredients": source["record"]["ingredients"] = []
    before = deepcopy(source)
    mock = MockMfdsClient(items=[OfficialItem("LOCAL_MOCK", "a", "가상알파정")])
    if failure == "multiple-matches": mock = MockMfdsClient(items=[OfficialItem("LOCAL_MOCK", x, "가상알파정") for x in ("a", "b")])
    with patch.object(mock, "search_by_name", side_effect=RuntimeError("private-sentinel")) if failure == "lookup-failure" else patch.object(mock, "last_failed", False):
        out = normalize_structured_record(source, mock, expected_family_member_id=FAMILY)
    assert source == before
    assert validate_common_result(out) == []
    assert "private-sentinel" not in str(out)
    if failure in {"missing-product", "family", "bad-decimal", "bad-ingredient-name", "bad-source-id", "bad-warning"}: assert out["status"] == "FAILED"
    elif failure == "lookup-failure": assert out["status"] == "UNMATCHED"
    else: assert out["status"] == "PARTIAL"


def test_empty_ingredient_contract_stays_unresolved_without_inventing_raw():
    source = extract(document("current"))[0]
    source["record"]["ingredients"] = []
    result = normalize_structured_record(source, MockMfdsClient(items=[]), expected_family_member_id=FAMILY)
    assert result["record"]["ingredients"] == []
    assert result["record"]["user_confirmed"] is False
