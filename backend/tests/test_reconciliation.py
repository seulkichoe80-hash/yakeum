import unittest

from backend.services.reconciliation import reconcile_records


FAMILY_ID = "family-virtual-001"
GENERATED_AT = "2026-10-05T00:00:00Z"


def ingredient(name, strength, *, official_id=None, unit="mg"):
    return {
        "ingredient_name_raw": name,
        "ingredient_name_normalized": name,
        "product_strength": strength,
        "product_strength_unit": unit,
        "official_ingredient_id": official_id,
    }


def record(
    product,
    strength,
    *,
    family_id=FAMILY_ID,
    mfds_product_id=None,
    drug_code=None,
    ingredients=None,
    dose="1",
    administrations="1",
):
    ingredients = ingredients or [ingredient(f"가상성분-{product}", strength)]
    return {
        "record_id": f"record-{product}-{strength}",
        "family_member_id": family_id,
        "source_type": "HIRA",
        "source_record_id": f"source-{product}-{strength}",
        "record_date": "2026-10-01",
        "dispensing_date": "2026-10-01",
        "prescribing_institution": "가상처방기관",
        "dispensing_institution": "가상조제기관",
        "product_name_raw": product,
        "product_name_normalized": product,
        "drug_code": drug_code,
        "drug_category": "가상분류",
        "unit": "정",
        "dose_per_administration": dose,
        "administrations_per_day": administrations,
        "duration_days": "7",
        "dosage_text_raw": None,
        "mfds_product_id": mfds_product_id,
        "ingredients": ingredients,
        "confidence": None,
        "user_confirmed": True,
    }


def reconcile(previous, current):
    return reconcile_records(previous, current, generated_at=GENERATED_AT)


class ReconciliationEngineTests(unittest.TestCase):
    def test_required_five_medication_scenario(self):
        previous = [
            record("A약", "5", mfds_product_id="MFDS-A"),
            record("B약", "10", mfds_product_id="MFDS-B"),
            record("C약", "20", mfds_product_id="MFDS-C"),
            record("D약", "5", mfds_product_id="MFDS-D"),
        ]
        current = [
            record("A약", "5", mfds_product_id="MFDS-A"),
            record("B약", "20", mfds_product_id="MFDS-B"),
            record("C약", "20", mfds_product_id="MFDS-C"),
            record("E약", "10", mfds_product_id="MFDS-E"),
        ]

        result = reconcile(previous, current)

        self.assertEqual(
            [item["status"] for item in result["items"]],
            [
                "MAINTAINED",
                "DOSE_CHANGED",
                "MAINTAINED",
                "NEEDS_CONFIRMATION",
                "NEW",
            ],
        )
        self.assertEqual(result["family_member_id"], FAMILY_ID)
        self.assertEqual(result["generated_at"], GENERATED_AT)

    def test_same_mfds_product_id_matches(self):
        result = reconcile(
            [record("이전제품명", "5", mfds_product_id="MFDS-SAME")],
            [record("현재제품명", "5", mfds_product_id="MFDS-SAME")],
        )
        self.assertEqual(result["items"][0]["status"], "MAINTAINED")

    def test_same_drug_code_matches_when_mfds_id_is_missing(self):
        result = reconcile(
            [record("이전제품명", "5", drug_code="00001234")],
            [record("현재제품명", "5", drug_code="00001234")],
        )
        self.assertEqual(result["items"][0]["status"], "MAINTAINED")

    def test_same_ingredient_with_different_product_ids_does_not_match(self):
        shared = [ingredient("공통가상성분", "5")]
        result = reconcile(
            [record("가상제품", "5", mfds_product_id="MFDS-ONE", ingredients=shared)],
            [record("가상제품", "5", mfds_product_id="MFDS-TWO", ingredients=shared)],
        )
        self.assertEqual(
            [item["status"] for item in result["items"]],
            ["NEEDS_CONFIRMATION", "NEW"],
        )

    def test_compound_ingredient_order_does_not_change_identity(self):
        first = ingredient("가상성분1", "5")
        second = ingredient("가상성분2", "10")
        result = reconcile(
            [record("가상복합제", None, ingredients=[first, second])],
            [record("가상복합제", None, ingredients=[second, first])],
        )
        self.assertEqual(result["items"][0]["status"], "MAINTAINED")

    def test_strength_value_to_null_is_not_dose_changed(self):
        result = reconcile(
            [record("가상제품", "5", mfds_product_id="MFDS-NULL-1")],
            [record("가상제품", None, mfds_product_id="MFDS-NULL-1")],
        )
        self.assertEqual(result["items"][0]["status"], "MAINTAINED")

    def test_strength_null_to_value_is_not_dose_changed(self):
        result = reconcile(
            [record("가상제품", None, mfds_product_id="MFDS-NULL-2")],
            [record("가상제품", "5", mfds_product_id="MFDS-NULL-2")],
        )
        self.assertEqual(result["items"][0]["status"], "MAINTAINED")

    def test_dose_value_on_one_side_null_is_not_dose_changed(self):
        previous = record("가상제품", "5", mfds_product_id="MFDS-DOSE", dose="1")
        current = record("가상제품", "5", mfds_product_id="MFDS-DOSE", dose=None)
        result = reconcile([previous], [current])
        self.assertEqual(result["items"][0]["status"], "MAINTAINED")

    def test_comparable_dose_change_is_dose_changed(self):
        result = reconcile(
            [record("가상제품", "5", mfds_product_id="MFDS-DOSE-CHANGE", dose="1")],
            [record("가상제품", "5", mfds_product_id="MFDS-DOSE-CHANGE", dose="2")],
        )
        self.assertEqual(result["items"][0]["status"], "DOSE_CHANGED")

    def test_different_family_members_are_rejected(self):
        with self.assertRaises(ValueError):
            reconcile(
                [record("가상제품", "5", family_id="family-one")],
                [record("가상제품", "5", family_id="family-two")],
            )

    def test_previous_only_record_needs_confirmation(self):
        result = reconcile(
            [record("과거가상제품", "5", mfds_product_id="MFDS-PAST")], []
        )
        self.assertEqual(result["items"][0]["status"], "NEEDS_CONFIRMATION")
        self.assertEqual(
            result["items"][0]["reason_code"], "NOT_FOUND_IN_LATEST_SOURCE"
        )

    def test_current_only_record_is_new(self):
        result = reconcile(
            [], [record("현재가상제품", "5", mfds_product_id="MFDS-CURRENT")]
        )
        self.assertEqual(result["items"][0]["status"], "NEW")
        self.assertEqual(result["items"][0]["reason_code"], "NEW_RECORD")

    def test_ingredients_alone_do_not_confirm_product_identity(self):
        shared = [ingredient("공통가상성분", "5")]
        previous = record("서로다른제품1", "5", ingredients=shared)
        current = record("서로다른제품2", "5", ingredients=shared)
        result = reconcile([previous], [current])
        self.assertEqual(
            [item["status"] for item in result["items"]],
            ["NEEDS_CONFIRMATION", "NEW"],
        )

    def test_output_uses_only_contract_statuses(self):
        result = reconcile(
            [record("과거제품", "5", mfds_product_id="MFDS-OLD")],
            [record("현재제품", "5", mfds_product_id="MFDS-NEW")],
        )
        allowed = {"MAINTAINED", "NEW", "DOSE_CHANGED", "NEEDS_CONFIRMATION"}
        self.assertTrue(all(item["status"] in allowed for item in result["items"]))


if __name__ == "__main__":
    unittest.main()
