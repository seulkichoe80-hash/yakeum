import json
import unittest

from backend.services.extraction import (
    ExtractionContext,
    GeminiConfigurationError,
    GeminiSettings,
    adapt_gemini_response,
    adapt_provider_call,
)
from backend.services.extraction.prompt import SYSTEM_PROMPT


FAMILY_ID = "00000000-0000-4000-8000-000000000001"
OTHER_FAMILY_ID = "00000000-0000-4000-8000-000000000002"
RECORD_ID = "10000000-0000-4000-8000-000000000001"
CONTEXT = ExtractionContext(
    family_member_id=FAMILY_ID,
    source_document_id="virtual-image-001",
    record_date="2026-10-14",
)


def medication(**overrides):
    value = {
        "product_name_raw": "가상제품A",
        "ingredients": [
            {
                "ingredient_name_raw": "가상성분A",
                "product_strength": "100",
                "product_strength_unit": "mg",
            }
        ],
        "unit": "정",
        "dose_per_administration": "1",
        "administrations_per_day": "2",
        "duration_days": "7",
        "dosage_text_raw": "하루 두 번 한 정",
        "confidence": "0.91",
    }
    value.update(overrides)
    return value


def response(*medications, document_type="약봉투", family_member_id=None):
    value = {"document_type": document_type, "medications": list(medications)}
    if family_member_id is not None:
        value["family_member_id"] = family_member_id
    return json.dumps(value, ensure_ascii=False)


def adapt(raw, context=CONTEXT):
    return adapt_gemini_response(
        raw,
        context,
        record_id_factory=lambda _family_id, _source_record_id: RECORD_ID,
    )


class ExtractionContractTests(unittest.TestCase):
    def test_single_product_success(self):
        result = adapt(response(medication()))[0]

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["record"]["product_name_raw"], "가상제품A")
        self.assertEqual(result["record"]["source_type"], "MEDICINE_BAG")

    def test_multiple_products_return_one_contract_result_per_product(self):
        results = adapt(
            response(
                medication(product_name_raw="가상제품A"),
                medication(product_name_raw="가상제품B"),
            )
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(
            [item["record"]["source_record_id"] for item in results],
            ["virtual-image-001:1", "virtual-image-001:2"],
        )

    def test_missing_product_name_is_not_invented(self):
        result = adapt(response(medication(product_name_raw=None)))[0]

        self.assertEqual(result["status"], "NEEDS_CONFIRMATION")
        self.assertIsNone(result["record"])
        self.assertEqual(result["warnings"][0]["field"], "product_name_raw")

    def test_unknown_document_type_is_not_treated_as_medicine_bag(self):
        result = adapt(response(medication(), document_type="알 수 없는 자료"))[0]

        self.assertEqual(result["status"], "NEEDS_CONFIRMATION")
        self.assertIsNone(result["record"])
        self.assertEqual(result["warnings"][0]["field"], "source_type")

    def test_missing_confidence_stays_null_and_needs_confirmation(self):
        result = adapt(response(medication(confidence=None)))[0]

        self.assertEqual(result["status"], "NEEDS_CONFIRMATION")
        self.assertIsNone(result["record"]["confidence"])
        self.assertEqual(result["warnings"][0]["field"], "confidence")

    def test_invalid_json_returns_failed_without_source_text(self):
        raw = "not-json-with-private-placeholder"
        result = adapt(raw)[0]

        self.assertEqual(result["status"], "FAILED")
        self.assertIsNone(result["record"])
        self.assertNotIn(raw, result["errors"][0]["message"])

    def test_provider_error_is_sanitized(self):
        def failing_provider():
            raise RuntimeError("API key SECRET-VALUE and private payload")

        result = adapt_provider_call(failing_provider, CONTEXT)[0]

        self.assertEqual(result["status"], "FAILED")
        self.assertNotIn("SECRET-VALUE", result["errors"][0]["message"])
        self.assertNotIn("private payload", result["errors"][0]["message"])

    def test_multiple_ingredients_are_preserved_as_raw_candidates(self):
        ingredients = [
            {
                "ingredient_name_raw": "가상성분A",
                "product_strength": "10",
                "product_strength_unit": "mg",
            },
            {
                "ingredient_name_raw": "가상성분B",
                "product_strength": "20.5",
                "product_strength_unit": "mg",
            },
        ]
        record = adapt(response(medication(ingredients=ingredients)))[0]["record"]

        self.assertEqual(len(record["ingredients"]), 2)
        self.assertEqual(record["ingredients"][1]["product_strength"], "20.5")
        self.assertTrue(
            all(item["ingredient_name_normalized"] is None for item in record["ingredients"])
        )

    def test_product_strength_and_administration_dose_stay_separate(self):
        record = adapt(
            response(
                medication(
                    ingredients=[
                        {
                            "ingredient_name_raw": "가상성분A",
                            "product_strength": "200",
                            "product_strength_unit": "mg",
                        }
                    ],
                    dose_per_administration="1",
                    unit="정",
                )
            )
        )[0]["record"]

        self.assertEqual(record["ingredients"][0]["product_strength"], "200")
        self.assertEqual(record["dose_per_administration"], "1")
        self.assertEqual(record["unit"], "정")

    def test_missing_caller_family_id_fails(self):
        context = ExtractionContext(
            family_member_id="",
            source_document_id="virtual-image-001",
            record_date="2026-10-14",
        )
        result = adapt(response(medication()), context)[0]

        self.assertEqual(result["status"], "FAILED")
        self.assertIsNone(result["record"])

    def test_claimed_family_mismatch_fails_entire_document(self):
        result = adapt(
            response(medication(), family_member_id=OTHER_FAMILY_ID)
        )[0]

        self.assertEqual(result["status"], "FAILED")
        self.assertIn("가족 범위", result["errors"][0]["message"])

    def test_records_are_always_unconfirmed_and_official_fields_are_null(self):
        record = adapt(response(medication()))[0]["record"]

        self.assertFalse(record["user_confirmed"])
        self.assertIsNone(record["product_name_normalized"])
        self.assertIsNone(record["mfds_product_id"])
        self.assertIsNone(record["ingredients"][0]["official_ingredient_id"])

    def test_legacy_a_team_name_and_instructions_remain_raw(self):
        legacy = {
            "name": "가상 이전형식 제품",
            "instructions": "표시된 복용법",
            "ingredients": [
                {"name": "가상 이전형식 성분", "product_strength": None}
            ],
            "confidence": "0.8",
        }
        record = adapt(response(legacy))[0]["record"]

        self.assertEqual(record["product_name_raw"], "가상 이전형식 제품")
        self.assertEqual(record["dosage_text_raw"], "표시된 복용법")
        self.assertEqual(
            record["ingredients"][0]["ingredient_name_raw"],
            "가상 이전형식 성분",
        )

    def test_model_and_api_key_must_be_explicit_environment_values(self):
        with self.assertRaises(GeminiConfigurationError):
            GeminiSettings.from_environment({})

        settings = GeminiSettings.from_environment(
            {
                "YAKEUM_GEMINI_MODEL": "account-verified-model",
                "GEMINI_API_KEY": "virtual-secret",
            }
        )
        self.assertEqual(settings.model_name, "account-verified-model")
        self.assertEqual(settings.api_key, "virtual-secret")

    def test_prompt_excludes_patient_identity_and_medical_judgement(self):
        self.assertNotIn("patient_name", SYSTEM_PROMPT)
        self.assertNotIn("raw_text", SYSTEM_PROMPT)
        self.assertIn("환자 이름", SYSTEM_PROMPT)
        self.assertIn("수집하지 않을 정보", SYSTEM_PROMPT)
        self.assertIn("복용 중단", SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
