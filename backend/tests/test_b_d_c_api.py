from __future__ import annotations

from io import BytesIO

import openpyxl
import pytest
from httpx import ASGITransport, AsyncClient

from backend.api.main import MAX_FILE_BYTES, app


FAMILY_ID = "00000000-0000-4000-8000-000000000001"
pytestmark = pytest.mark.anyio
HEADERS = [
    "번호",
    "조제일자",
    "처방기관",
    "조제기관",
    "제품명",
    "약효분류",
    "성분명",
    "약품코드",
    "단위",
    "1회 투약량",
    "1일 투여횟수",
    "총 투약일수",
]


def _xlsx(rows: list[list[object]]) -> bytes:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "가상 투약이력"
    sheet.append(["약이음 가상 테스트 자료"])
    sheet.append(HEADERS)
    for row in rows:
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def _row(
    number: int,
    date: str,
    product: str | None,
    code: str | None,
    dose: object = "1",
    ingredient: str | None = None,
) -> list[object]:
    return [
        number,
        date,
        "가상처방기관",
        "가상조제기관",
        product,
        "가상분류",
        ingredient or (f"가상성분{number}" if product else None),
        code,
        "정",
        dose,
        "1",
        "7",
    ]


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _post(
    previous: bytes,
    current: bytes,
    *,
    family_member_id: str = FAMILY_ID,
    previous_name: str = "previous.xlsx",
    current_name: str = "current.xlsx",
):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.post(
            "/api/v1/reconciliations/hira",
            data={"family_member_id": family_member_id},
            files={
                "previous_file": (
                    previous_name,
                    previous,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
                "current_file": (
                    current_name,
                    current,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            },
        )


def _four_state_files() -> tuple[bytes, bytes]:
    previous = _xlsx(
        [
            _row(1, "2026-08-01", "가상제품A", "000000001", "1"),
            _row(2, "2026-08-01", "가상제품B", "000000002", "1"),
            _row(3, "2026-08-01", "가상제품C", "000000003", "1"),
        ]
    )
    current = _xlsx(
        [
            _row(1, "2026-09-01", "가상제품A", "000000001", "1"),
            _row(2, "2026-09-01", "가상제품B", "000000002", "2"),
            _row(4, "2026-09-01", "가상제품D", "000000004", "1"),
        ]
    )
    return previous, current


async def test_multipart_virtual_hira_flow_returns_all_four_states():
    response = await _post(*_four_state_files())

    assert response.status_code == 200
    body = response.json()
    assert body["processing"] == {
        "parser": "DETERMINISTIC",
        "file_processing": "EXECUTED",
        "official_data_mode": "LOCAL_MOCK",
        "persisted": False,
    }
    assert {item["status"] for item in body["reconciliation_result"]["items"]} == {
        "MAINTAINED",
        "NEW",
        "DOSE_CHANGED",
        "NEEDS_CONFIRMATION",
    }


async def test_current_intake_starts_unknown_and_pending():
    response = await _post(*_four_state_files())
    states = response.json()["current_intake_states"]

    assert states
    assert {state["intake_status"] for state in states} == {"UNKNOWN"}
    assert {state["verification_status"] for state in states} == {"PENDING"}
    assert all(state["verified_by"] is None for state in states)
    assert all(state["last_verified_at"] is None for state in states)


async def test_failed_rows_are_separate_from_reconciliation():
    previous, current = _four_state_files()
    current_with_failure = _xlsx(
        [
            _row(1, "2026-09-01", "가상제품A", "000000001"),
            _row(9, "2026-09-01", None, "000000009"),
        ]
    )
    response = await _post(previous, current_with_failure)
    body = response.json()

    assert response.status_code == 200
    assert len(body["review_results"]["current"]) == 1
    assert body["review_results"]["current"][0]["status"] == "FAILED"
    assert all(
        item["status"] != "FAILED"
        for item in body["reconciliation_result"]["items"]
    )


async def test_partial_and_unmatched_results_keep_warnings_and_raw_record():
    previous = _xlsx([_row(1, "2026-08-01", "가상제품A", "000000001")])
    current = _xlsx(
        [
            _row(1, "2026-09-01", "가상제품A", "000000001"),
            _row(2, "2026-09-01", "가나릴", None, ingredient="가짜성분"),
        ]
    )
    response = await _post(previous, current)
    accepted = response.json()["accepted_results"]["current"]

    assert response.status_code == 200
    assert {result["status"] for result in accepted} >= {"PARTIAL", "UNMATCHED"}
    for result in accepted:
        if result["status"] in {"PARTIAL", "UNMATCHED"}:
            assert result["record"]["product_name_raw"]
            assert result["warnings"]


async def test_null_strength_is_preserved_without_false_dose_change():
    previous = _xlsx([_row(1, "2026-08-01", "가상제품A", "000000001")])
    current = _xlsx([_row(1, "2026-09-01", "가상제품A", "000000001")])
    response = await _post(previous, current)
    body = response.json()

    assert body["reconciliation_result"]["items"][0]["status"] == "MAINTAINED"
    ingredient = body["accepted_results"]["current"][0]["record"]["ingredients"][0]
    assert ingredient["product_strength"] is None


async def test_repeated_rows_are_not_removed():
    duplicate = _row(1, "2026-08-01", "가상제품A", "000000001")
    previous = _xlsx([duplicate, duplicate])
    current = _xlsx([_row(1, "2026-09-01", "가상제품A", "000000001")])
    response = await _post(previous, current)

    assert len(response.json()["accepted_results"]["previous"]) == 2


async def test_all_failed_rows_return_empty_result_and_review_items():
    failed = _xlsx([_row(1, "2026-08-01", None, "000000001")])
    response = await _post(failed, failed)
    body = response.json()

    assert response.status_code == 200
    assert body["reconciliation_result"]["items"] == []
    assert body["current_intake_states"] == []
    assert len(body["review_results"]["previous"]) == 1
    assert len(body["review_results"]["current"]) == 1


async def test_wrong_extension_is_rejected():
    valid = _xlsx([_row(1, "2026-08-01", "가상제품A", "000000001")])
    response = await _post(valid, valid, previous_name="previous.xls")
    assert response.status_code == 415


async def test_corrupted_xlsx_is_rejected():
    valid = _xlsx([_row(1, "2026-08-01", "가상제품A", "000000001")])
    response = await _post(b"not-an-xlsx", valid)
    assert response.status_code == 400


async def test_empty_file_is_rejected():
    valid = _xlsx([_row(1, "2026-08-01", "가상제품A", "000000001")])
    response = await _post(b"", valid)
    assert response.status_code == 400


async def test_oversized_file_is_rejected():
    valid = _xlsx([_row(1, "2026-08-01", "가상제품A", "000000001")])
    response = await _post(b"x" * (MAX_FILE_BYTES + 1), valid)
    assert response.status_code == 413


async def test_invalid_family_id_is_rejected():
    previous, current = _four_state_files()
    response = await _post(previous, current, family_member_id="not-a-uuid")
    assert response.status_code == 422
