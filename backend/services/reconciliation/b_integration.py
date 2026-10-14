"""Internal B-to-D integration PoC.

The caller supplies previous and current NormalizationResult batches explicitly.
This module never infers the comparison boundary from record dates, collapses
repeat dispensing records, or changes the source results.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .engine import reconcile_records


NormalizationResult = Mapping[str, Any]

_ACCEPTED_STATUSES = frozenset({"MATCHED", "PARTIAL", "UNMATCHED"})
_KNOWN_STATUSES = _ACCEPTED_STATUSES | {"FAILED"}


def reconcile_normalization_results(
    previous_results: Sequence[NormalizationResult],
    current_results: Sequence[NormalizationResult],
    family_member_id: str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Prepare B results and run D reconciliation without mutating inputs.

    ``PARTIAL`` and ``UNMATCHED`` records remain eligible for reconciliation;
    their complete NormalizationResult envelopes stay in ``accepted_results``
    so warnings and raw values remain available. ``FAILED`` results never enter
    D and are retained in ``review_results`` for separate confirmation.
    """

    expected_family_id = _required_text(family_member_id, "family_member_id")
    previous = _prepare_batch(previous_results, expected_family_id)
    current = _prepare_batch(current_results, expected_family_id)

    reconciliation_result = reconcile_records(
        previous["records"],
        current["records"],
        generated_at=generated_at,
    )

    return {
        "accepted_results": {
            "previous": previous["accepted_results"],
            "current": current["accepted_results"],
        },
        "review_results": {
            "previous": previous["review_results"],
            "current": current["review_results"],
        },
        "reconciliation_result": reconciliation_result,
    }


def _prepare_batch(
    results: Sequence[NormalizationResult], expected_family_id: str
) -> dict[str, list[dict[str, Any]]]:
    if isinstance(results, (str, bytes)) or not isinstance(results, Sequence):
        raise ValueError("NormalizationResult batch must be a sequence")

    records: list[dict[str, Any]] = []
    accepted_results: list[dict[str, Any]] = []
    review_results: list[dict[str, Any]] = []

    for result in results:
        if not isinstance(result, Mapping):
            raise ValueError("each NormalizationResult must be a mapping")

        status = result.get("status")
        if status not in _KNOWN_STATUSES:
            raise ValueError(f"unsupported NormalizationResult status: {status!r}")

        if status == "FAILED":
            review_results.append(deepcopy(dict(result)))
            continue

        record = result.get("record")
        if not isinstance(record, Mapping):
            raise ValueError(f"{status} NormalizationResult must contain a record")

        record_family_id = _required_text(
            record.get("family_member_id"), "MedicationRecord.family_member_id"
        )
        if record_family_id != expected_family_id:
            raise ValueError("cannot mix MedicationRecords from different families")

        accepted_results.append(deepcopy(dict(result)))
        records.append(deepcopy(dict(record)))

    return {
        "records": records,
        "accepted_results": accepted_results,
        "review_results": review_results,
    }


def _required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()
