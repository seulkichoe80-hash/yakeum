"""Current Intake State PoC.

This module keeps user-reported intake state separate from reconciliation
observations. It does not make medical decisions or infer whether a medication
is currently being taken from a reconciliation status.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


class IntakeStatus(str, Enum):
    """User-reported current intake status."""

    TAKING = "TAKING"
    NOT_TAKING = "NOT_TAKING"
    UNKNOWN = "UNKNOWN"


class VerificationStatus(str, Enum):
    """Whether a user has explicitly verified the intake status."""

    PENDING = "PENDING"
    USER_VERIFIED = "USER_VERIFIED"


def build_current_intake_states(
    reconciliation_result: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Create unverified Current Intake States without changing the input.

    A current record is used when present. For ``NEEDS_CONFIRMATION`` items
    without a current record, the previous record is the reference record.
    Reconciliation status never implies TAKING or NOT_TAKING.
    """

    family_member_id = _required_text(
        reconciliation_result.get("family_member_id"), "family_member_id"
    )
    items = reconciliation_result.get("items")
    if not isinstance(items, list):
        raise ValueError("reconciliation_result.items must be a list")

    states: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, Mapping):
            raise ValueError("each reconciliation item must be a mapping")

        record = _reference_record(item)
        record_family_id = _required_text(
            record.get("family_member_id"), "MedicationRecord.family_member_id"
        )
        if record_family_id != family_member_id:
            raise ValueError("MedicationRecord family_member_id does not match result")

        states.append(
            {
                "family_member_id": family_member_id,
                "medication_record_id": _required_text(
                    record.get("record_id"), "MedicationRecord.record_id"
                ),
                "intake_status": IntakeStatus.UNKNOWN.value,
                "verification_status": VerificationStatus.PENDING.value,
                "verified_by": None,
                "last_verified_at": None,
            }
        )

    return states


def apply_user_verification(
    current_state: Mapping[str, Any],
    intake_status: str | IntakeStatus,
    *,
    family_member_id: str,
    verified_by: str,
    last_verified_at: str,
) -> dict[str, Any]:
    """Return a verified state copy from an explicit user selection."""

    state_family_id = _required_text(
        current_state.get("family_member_id"), "current_state.family_member_id"
    )
    if _required_text(family_member_id, "family_member_id") != state_family_id:
        raise ValueError("cannot apply verification for a different family member")

    try:
        selected_status = IntakeStatus(intake_status)
    except (TypeError, ValueError) as error:
        raise ValueError("intake_status must be TAKING, NOT_TAKING, or UNKNOWN") from error

    verifier = _required_text(verified_by, "verified_by")
    verified_at = _validated_utc_timestamp(last_verified_at)

    verified_state = deepcopy(dict(current_state))
    verified_state.update(
        {
            "intake_status": selected_status.value,
            "verification_status": VerificationStatus.USER_VERIFIED.value,
            "verified_by": verifier,
            "last_verified_at": verified_at,
        }
    )
    return verified_state


def _reference_record(item: Mapping[str, Any]) -> Mapping[str, Any]:
    current_record = item.get("current_record")
    if isinstance(current_record, Mapping):
        return current_record

    previous_record = item.get("previous_record")
    if isinstance(previous_record, Mapping):
        return previous_record

    raise ValueError("reconciliation item must reference a MedicationRecord")


def _required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _validated_utc_timestamp(value: Any) -> str:
    timestamp = _required_text(value, "last_verified_at")
    iso_value = timestamp[:-1] + "+00:00" if timestamp.endswith("Z") else timestamp
    try:
        parsed = datetime.fromisoformat(iso_value)
    except ValueError as error:
        raise ValueError("last_verified_at must be an ISO 8601 UTC timestamp") from error

    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("last_verified_at must be an ISO 8601 UTC timestamp")
    return timestamp
