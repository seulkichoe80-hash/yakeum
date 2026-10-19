"""Orchestration for the local HIRA B-to-D-to-C Vertical Slice."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.services.mfds.mock_client import MockMfdsClient
from backend.services.normalization.adapter import to_common_results
from backend.services.normalization.service import normalize_hira_file
from backend.services.reconciliation.b_integration import (
    reconcile_normalization_results,
)
from backend.services.reconciliation.current_intake import (
    build_current_intake_states,
)


def process_hira_comparison(
    previous_path: Path,
    current_path: Path,
    family_member_id: str,
    *, version: int = 1,
) -> dict[str, Any]:
    """Run deterministic local processing without persistence or network I/O."""

    previous_internal = normalize_hira_file(previous_path, client=MockMfdsClient())
    current_internal = normalize_hira_file(current_path, client=MockMfdsClient())
    previous_results = to_common_results(previous_internal, family_member_id)
    current_results = to_common_results(current_internal, family_member_id)
    if version == 2:
        from backend.api.hira_hold import process_guarded
        return process_guarded(previous_results, current_results,
                               previous_internal, current_internal, family_member_id)
    integrated = reconcile_normalization_results(
        previous_results,
        current_results,
        family_member_id,
    )
    integrated["processing"] = {
        "parser": "DETERMINISTIC",
        "file_processing": "EXECUTED",
        "official_data_mode": "LOCAL_MOCK",
        "persisted": False,
    }
    integrated["current_intake_states"] = build_current_intake_states(
        integrated["reconciliation_result"]
    )
    return {
        "processing": integrated["processing"],
        "accepted_results": integrated["accepted_results"],
        "review_results": integrated["review_results"],
        "reconciliation_result": integrated["reconciliation_result"],
        "current_intake_states": integrated["current_intake_states"],
    }
