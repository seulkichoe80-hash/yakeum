"""D provider wiring tests: no real credentials, images or external requests."""

import json
import unittest
from unittest.mock import patch

from backend.api import extraction_provider as provider
from backend.services.extraction import ExtractionContext, GeminiSettings


class ExtractionProviderTests(unittest.TestCase):
    def setUp(self):
        self.context = ExtractionContext(
            "00000000-0000-4000-8000-000000000001", "virtual-document", "2026-10-19"
        )

    def test_provider_response_reaches_shared_adapter_without_confirmation(self):
        payload = json.dumps({"document_type": "약봉투", "medications": [
            {"name": "가상제품", "confidence": "0.8", "instructions": "가상 원문"},
            {"product_name_raw": "가상제품2", "confidence": "0.9", "ingredients": [
                {"ingredient_name_raw": "가상성분", "product_strength": "0.50", "product_strength_unit": "mg"}
            ]},
        ]})
        settings = GeminiSettings("fake-model", "not-a-real-key")
        with patch.object(GeminiSettings, "from_environment", return_value=settings), patch.object(
            provider, "_request_gemini", return_value=payload
        ) as request:
            results = provider.extract_image_candidates(b"virtual-image", "image/png", self.context)
        request.assert_called_once_with(b"virtual-image", "image/png", settings)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["record"]["dosage_text_raw"], "가상 원문")
        self.assertEqual(results[1]["record"]["ingredients"][0]["product_strength"], "0.5")
        self.assertTrue(all(not result["record"]["user_confirmed"] for result in results))
        self.assertIsNone(results[0]["record"]["mfds_product_id"])

    def test_invalid_images_never_load_settings_or_call_provider(self):
        with patch.object(GeminiSettings, "from_environment") as settings, patch.object(provider, "_request_gemini") as request:
            for data, mime in [(b"", "image/png"), (b"virtual", "application/pdf"), (b"x" * (provider.MAX_IMAGE_BYTES + 1), "image/png")]:
                with self.subTest(mime=mime, size=len(data)):
                    self.assertEqual(provider.extract_image_candidates(data, mime, self.context)[0]["status"], "FAILED")
        settings.assert_not_called()
        request.assert_not_called()

    def test_invalid_context_prevents_external_request(self):
        with patch.object(provider, "_request_gemini") as request:
            result = provider.extract_image_candidates(b"virtual", "image/png", ExtractionContext("bad", "doc", "2026-10-19"))
        request.assert_not_called()
        self.assertEqual(result[0]["status"], "FAILED")

    def test_configuration_and_provider_errors_are_sanitized(self):
        for method in ["configuration", "provider"]:
            with self.subTest(method=method), patch.object(
                GeminiSettings, "from_environment",
                side_effect=RuntimeError("private-marker") if method == "configuration" else None,
                return_value=GeminiSettings("fake-model", "not-a-real-key"),
            ), patch.object(provider, "_request_gemini", side_effect=RuntimeError("private-marker")):
                result = provider.extract_image_candidates(b"virtual", "image/png", self.context)
            self.assertEqual(result[0]["status"], "FAILED")
            self.assertNotIn("private-marker", json.dumps(result))

    def test_malformed_response_is_not_success(self):
        with patch.object(GeminiSettings, "from_environment"), patch.object(provider, "_request_gemini", return_value="not json"):
            result = provider.extract_image_candidates(b"virtual", "image/png", self.context)
        self.assertEqual(result[0]["status"], "FAILED")
