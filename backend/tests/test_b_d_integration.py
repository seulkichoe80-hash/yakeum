import copy
import tempfile
import unittest
from pathlib import Path

from backend.services.hira.tests.make_fixtures import make_common_sample_xlsx
from backend.services.normalization.adapter import to_common_results
from backend.services.normalization.service import normalize_hira_file
from backend.services.reconciliation import reconcile_normalization_results


FAMILY_ID = "00000000-0000-4000-8000-000000000001"
OTHER_FAMILY_ID = "00000000-0000-4000-8000-000000000002"
GENERATED_AT = "2026-10-14T00:00:00Z"


def ingredient(strength="5"):
    return {
        "ingredient_name_raw": "가상성분",
        "ingredient_name_normalized": "가상성분",
        "product_strength": strength,
        "product_strength_unit": "mg" if strength is not None else None,
        "official_ingredient_id": "VIRTUAL-INGREDIENT",
    }


def record(
    record_id,
    *,
    product_id="VIRTUAL-PRODUCT",
    family_id=FAMILY_ID,
    dose="1",
    strength="5",
    record_date="2026-10-01",
):
    return {
        "record_id": record_id,
        "family_member_id": family_id,
        "source_type": "HIRA",
        "source_record_id": f"source-{record_id}",
        "record_date": record_date,
        "dispensing_date": record_date,
        "prescribing_institution": "가상처방기관",
        "dispensing_institution": "가상조제기관",
        "product_name_raw": f"가상제품 {strength or ''}mg".strip(),
        "product_name_normalized": "가상제품",
        "drug_code": f"CODE-{product_id}",
        "drug_category": "가상분류",
        "unit": "정",
        "dose_per_administration": dose,
        "administrations_per_day": "1",
        "duration_days": "7",
        "dosage_text_raw": None,
        "mfds_product_id": product_id,
        "ingredients": [ingredient(strength)],
        "confidence": None,
        "user_confirmed": False,
    }


def result(status, medication_record=None, *, warnings=None, errors=None):
    return {
        "status": status,
        "record": medication_record,
        "match": {
            "source": "MFDS_DRUG" if status == "MATCHED" else None,
            "official_id": (
                medication_record.get("mfds_product_id")
                if status == "MATCHED" and medication_record
                else None
            ),
            "match_method": "CODE_EXACT" if status == "MATCHED" else None,
        },
        "warnings": list(warnings or []),
        "errors": list(errors or []),
    }


def reconcile(previous, current):
    return reconcile_normalization_results(
        previous,
        current,
        FAMILY_ID,
        generated_at=GENERATED_AT,
    )


class BToDIntegrationTests(unittest.TestCase):
    def test_same_medication_and_dosage_is_maintained(self):
        output = reconcile(
            [result("MATCHED", record("previous"))],
            [result("MATCHED", record("current"))],
        )
        item = output["reconciliation_result"]["items"][0]
        self.assertEqual(item["status"], "MAINTAINED")
        self.assertEqual(item["reason_code"], "SAME_INGREDIENT_SAME_STRENGTH")

    def test_dose_change_is_dose_changed(self):
        output = reconcile(
            [result("MATCHED", record("previous", dose="1"))],
            [result("MATCHED", record("current", dose="2"))],
        )
        self.assertEqual(
            output["reconciliation_result"]["items"][0]["status"],
            "DOSE_CHANGED",
        )

    def test_previous_only_medication_needs_confirmation(self):
        output = reconcile([result("MATCHED", record("previous"))], [])
        item = output["reconciliation_result"]["items"][0]
        self.assertEqual(item["status"], "NEEDS_CONFIRMATION")
        self.assertEqual(item["reason_code"], "NOT_FOUND_IN_LATEST_SOURCE")

    def test_current_only_medication_is_new(self):
        output = reconcile([], [result("MATCHED", record("current"))])
        self.assertEqual(
            output["reconciliation_result"]["items"][0]["status"], "NEW"
        )

    def test_null_strength_is_preserved_and_not_a_dose_change(self):
        output = reconcile(
            [result("MATCHED", record("previous", strength="5"))],
            [result("MATCHED", record("current", strength=None))],
        )
        item = output["reconciliation_result"]["items"][0]
        self.assertNotEqual(item["status"], "DOSE_CHANGED")
        self.assertIsNone(
            item["current_record"]["ingredients"][0]["product_strength"]
        )

    def test_repeat_dispensing_records_are_not_removed(self):
        previous = [
            result("PARTIAL", record("previous-1")),
            result("PARTIAL", record("previous-2")),
        ]
        current = [
            result("PARTIAL", record("current-1")),
            result("PARTIAL", record("current-2")),
        ]
        output = reconcile(previous, current)
        self.assertEqual(len(output["accepted_results"]["previous"]), 2)
        self.assertEqual(len(output["accepted_results"]["current"]), 2)
        self.assertEqual(len(output["reconciliation_result"]["items"]), 4)
        self.assertEqual(
            [item["status"] for item in output["reconciliation_result"]["items"]],
            ["NEEDS_CONFIRMATION", "NEEDS_CONFIRMATION", "NEW", "NEW"],
        )

    def test_failed_is_retained_for_review_and_excluded_from_d(self):
        failed = result(
            "FAILED",
            None,
            errors=[
                {
                    "code": "REQUIRED_FIELD_MISSING",
                    "message": "가상 필수값 누락",
                    "field": "product_name_raw",
                }
            ],
        )
        output = reconcile(
            [failed, result("UNMATCHED", record("previous"))],
            [result("UNMATCHED", record("current"))],
        )
        self.assertEqual(output["review_results"]["previous"], [failed])
        self.assertEqual(len(output["accepted_results"]["previous"]), 1)
        self.assertEqual(len(output["reconciliation_result"]["items"]), 1)

    def test_unmatched_raw_record_and_warnings_are_preserved(self):
        warning = {
            "code": "OFFICIAL_MATCH_NOT_FOUND",
            "message": "가상 공식 데이터 미매칭",
            "field": None,
        }
        unmatched = result(
            "UNMATCHED", record("current", product_id=None), warnings=[warning]
        )
        output = reconcile([], [unmatched])
        accepted = output["accepted_results"]["current"][0]
        self.assertEqual(accepted, unmatched)
        self.assertEqual(accepted["warnings"], [warning])
        self.assertEqual(accepted["record"]["product_name_raw"], "가상제품 5mg")

    def test_different_family_member_is_rejected(self):
        previous = [result("MATCHED", record("previous"))]
        current = [
            result(
                "MATCHED", record("current", family_id=OTHER_FAMILY_ID)
            )
        ]
        with self.assertRaises(ValueError):
            reconcile(previous, current)

    def test_inputs_are_not_mutated(self):
        previous = [result("PARTIAL", record("previous"), warnings=[{"x": 1}])]
        current = [result("UNMATCHED", record("current"))]
        original_previous = copy.deepcopy(previous)
        original_current = copy.deepcopy(current)
        reconcile(previous, current)
        self.assertEqual(previous, original_previous)
        self.assertEqual(current, original_current)

    def test_virtual_hira_excel_full_flow(self):
        with tempfile.TemporaryDirectory() as directory:
            excel_path = make_common_sample_xlsx(Path(directory) / "virtual_hira.xlsx")
            common_results = to_common_results(
                normalize_hira_file(excel_path), FAMILY_ID
            )

        output = reconcile(common_results, common_results)

        self.assertEqual(
            [item["status"] for item in common_results],
            ["MATCHED", "PARTIAL", "PARTIAL", "UNMATCHED", "FAILED", "FAILED"],
        )
        self.assertEqual(len(output["accepted_results"]["previous"]), 4)
        self.assertEqual(len(output["accepted_results"]["current"]), 4)
        self.assertEqual(len(output["review_results"]["previous"]), 2)
        self.assertEqual(len(output["review_results"]["current"]), 2)
        self.assertEqual(
            {item["status"] for item in output["reconciliation_result"]["items"]},
            {"MAINTAINED", "NEEDS_CONFIRMATION", "NEW"},
        )


if __name__ == "__main__":
    unittest.main()
