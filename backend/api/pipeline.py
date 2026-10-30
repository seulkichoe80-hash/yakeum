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
    *, version: int = 1, official_lookup=None,
) -> dict[str, Any]:
    """Default Mock; account-only explicit injected lookup may use the live path."""

    from backend.services.mfds.live_matching import NoLookup, verify_result
    client=NoLookup() if official_lookup is not None else MockMfdsClient()
    previous_internal = normalize_hira_file(previous_path, client=client)
    current_internal = normalize_hira_file(current_path, client=client)
    previous_results = to_common_results(previous_internal, family_member_id)
    current_results = to_common_results(current_internal, family_member_id)
    if official_lookup is not None:
        if version != 2: raise ValueError('Live matching requires explicit HIRA v2')
        previous_results=[verify_result(r,official_lookup) for r in previous_results]
        current_results=[verify_result(r,official_lookup) for r in current_results]
    if version == 2:
        from backend.api.hira_hold import process_guarded
        result=process_guarded(previous_results, current_results,
                               previous_internal, current_internal, family_member_id, official_mode="MFDS_LIVE" if official_lookup is not None else "LOCAL_MOCK")
        if official_lookup is not None:result["official_lookup"]=official_lookup.summary()
        return result
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
