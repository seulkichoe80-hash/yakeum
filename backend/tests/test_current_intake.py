import copy
import unittest

from backend.services.reconciliation import (
    IntakeStatus,
    VerificationStatus,
    apply_user_verification,
    build_current_intake_states,
)


FAMILY_ID = "family-virtual-001"
VERIFIED_AT = "2026-10-05T01:02:03Z"


def medication_record(record_id, *, family_id=FAMILY_ID):
    return {
        "record_id": record_id,
        "family_member_id": family_id,
        "product_name_normalized": "가상제품",
        "user_confirmed": True,
    }


def reconciliation_item(status, *, previous=None, current=None):
    return {
        "status": status,
        "previous_record": previous,
        "current_record": current,
        "reason_code": "VIRTUAL_REASON",
        "evidence": [],
    }


def reconciliation_result(*items, family_id=FAMILY_ID):
    return {
        "family_member_id": family_id,
        "generated_at": "2026-10-05T00:00:00Z",
        "items": list(items),
    }


def build_one(status, *, previous=None, current=None):
    result = reconciliation_result(
        reconciliation_item(status, previous=previous, current=current)
    )
    return build_current_intake_states(result)[0]


class CurrentIntakeStateTests(unittest.TestCase):
    def test_needs_confirmation_starts_unknown_and_pending(self):
        state = build_one(
            "NEEDS_CONFIRMATION", previous=medication_record("record-old")
        )
        self.assertEqual(state["intake_status"], "UNKNOWN")
        self.assertEqual(state["verification_status"], "PENDING")

    def test_new_does_not_automatically_become_taking(self):
        state = build_one("NEW", current=medication_record("record-new"))
        self.assertEqual(state["intake_status"], "UNKNOWN")

    def test_maintained_does_not_automatically_become_taking(self):
        state = build_one(
            "MAINTAINED",
            previous=medication_record("record-old"),
            current=medication_record("record-current"),
        )
        self.assertEqual(state["intake_status"], "UNKNOWN")

    def test_dose_changed_does_not_infer_intake_status(self):
        state = build_one(
            "DOSE_CHANGED",
            previous=medication_record("record-old"),
            current=medication_record("record-current"),
        )
        self.assertEqual(state["intake_status"], "UNKNOWN")
        self.assertEqual(state["verification_status"], "PENDING")

    def test_taking_selection_becomes_user_verified(self):
        state = build_one("NEW", current=medication_record("record-new"))
        verified = self._verify(state, IntakeStatus.TAKING)
        self.assertEqual(verified["intake_status"], "TAKING")
        self.assertEqual(verified["verification_status"], "USER_VERIFIED")

    def test_not_taking_selection_becomes_user_verified(self):
        state = build_one(
            "NEEDS_CONFIRMATION", previous=medication_record("record-old")
        )
        verified = self._verify(state, IntakeStatus.NOT_TAKING)
        self.assertEqual(verified["intake_status"], "NOT_TAKING")
        self.assertEqual(verified["verification_status"], "USER_VERIFIED")

    def test_unknown_selection_becomes_user_verified(self):
        state = build_one("NEW", current=medication_record("record-new"))
        verified = self._verify(state, IntakeStatus.UNKNOWN)
        self.assertEqual(verified["intake_status"], "UNKNOWN")
        self.assertEqual(verified["verification_status"], "USER_VERIFIED")

    def test_pending_state_has_no_verification_metadata(self):
        state = build_one("NEW", current=medication_record("record-new"))
        self.assertIsNone(state["verified_by"])
        self.assertIsNone(state["last_verified_at"])

    def test_user_verified_requires_verified_by(self):
        state = build_one("NEW", current=medication_record("record-new"))
        with self.assertRaises(ValueError):
            apply_user_verification(
                state,
                "TAKING",
                family_member_id=FAMILY_ID,
                verified_by="",
                last_verified_at=VERIFIED_AT,
            )

    def test_user_verified_requires_utc_timestamp(self):
        state = build_one("NEW", current=medication_record("record-new"))
        with self.assertRaises(ValueError):
            apply_user_verification(
                state,
                "TAKING",
                family_member_id=FAMILY_ID,
                verified_by="user-virtual-001",
                last_verified_at="2026-10-05T10:02:03+09:00",
            )

    def test_user_verification_does_not_mutate_reconciliation_result(self):
        result = reconciliation_result(
            reconciliation_item(
                "NEEDS_CONFIRMATION", previous=medication_record("record-old")
            )
        )
        original = copy.deepcopy(result)
        state = build_current_intake_states(result)[0]
        self._verify(state, "NOT_TAKING")
        self.assertEqual(result, original)
        self.assertEqual(result["items"][0]["status"], "NEEDS_CONFIRMATION")

    def test_verification_for_another_family_member_is_rejected(self):
        state = build_one("NEW", current=medication_record("record-new"))
        with self.assertRaises(ValueError):
            apply_user_verification(
                state,
                "TAKING",
                family_member_id="family-other",
                verified_by="user-virtual-001",
                last_verified_at=VERIFIED_AT,
            )

    def test_unallowed_user_selection_is_rejected(self):
        state = build_one("NEW", current=medication_record("record-new"))
        with self.assertRaises(ValueError):
            self._verify(state, "STOPPED")

    def test_needs_confirmation_uses_previous_record(self):
        state = build_one(
            "NEEDS_CONFIRMATION", previous=medication_record("record-old")
        )
        self.assertEqual(state["medication_record_id"], "record-old")

    def test_new_uses_current_record(self):
        state = build_one("NEW", current=medication_record("record-new"))
        self.assertEqual(state["medication_record_id"], "record-new")

    def test_result_and_record_family_mismatch_is_rejected(self):
        result = reconciliation_result(
            reconciliation_item(
                "NEW",
                current=medication_record("record-new", family_id="family-other"),
            )
        )
        with self.assertRaises(ValueError):
            build_current_intake_states(result)

    def test_user_verification_returns_copy_without_mutating_pending_state(self):
        state = build_one("NEW", current=medication_record("record-new"))
        verified = self._verify(state, "TAKING")
        self.assertEqual(state["verification_status"], "PENDING")
        self.assertEqual(verified["verified_by"], "user-virtual-001")
        self.assertEqual(verified["last_verified_at"], VERIFIED_AT)

    def test_state_enums_contain_only_mvp_values(self):
        self.assertEqual(
            {status.value for status in IntakeStatus},
            {"TAKING", "NOT_TAKING", "UNKNOWN"},
        )
        self.assertEqual(
            {status.value for status in VerificationStatus},
            {"PENDING", "USER_VERIFIED"},
        )

    def _verify(self, state, selection):
        return apply_user_verification(
            state,
            selection,
            family_member_id=FAMILY_ID,
            verified_by="user-virtual-001",
            last_verified_at=VERIFIED_AT,
        )


if __name__ == "__main__":
    unittest.main()
