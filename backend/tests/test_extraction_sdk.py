"""Real pinned SDK over an in-memory HTTP transport: zero external requests."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from google import genai
import httpx

from backend.api.extraction_provider import extract_image_candidates
from backend.services.extraction import ExtractionContext, GeminiSettings
from backend.services.extraction.sdk import count_analysis_requests, request_image
from backend.services.extraction.scripts.run_image import main


class SdkTransportTests(unittest.TestCase):
    def setUp(self):
        self.context = ExtractionContext('00000000-0000-4000-8000-000000000001',
                                         'synthetic-document', '2026-10-22')
        self.settings = GeminiSettings('fake-model', 'fake-test-key')
        self.calls = []
        self.real_client = genai.Client

    @contextlib.contextmanager
    def transport(self, status, body):
        def handler(request):
            self.calls.append(request)
            return httpx.Response(status, json=body)

        def client(*args, **kwargs):
            options = kwargs['http_options']
            self.assertEqual(options.retry_options.attempts, 1)
            self.assertEqual(options.timeout, 60000)
            self.assertFalse(kwargs['vertexai'])
            options.client_args['transport'] = httpx.MockTransport(handler)
            # Ignore host proxy settings in this in-memory transport test.
            options.client_args['trust_env'] = False
            return self.real_client(*args, **kwargs)

        with patch.object(genai, 'Client', side_effect=client), patch.dict(
            os.environ, {'GEMINI_API_KEY': self.settings.api_key,
                         'YAKEUM_GEMINI_MODEL': self.settings.model_name}, clear=False):
            yield

    def test_real_sdk_response_reaches_common_contract_once(self):
        payload = json.dumps({'document_type': '약봉투', 'medications': [
            {'product_name_raw': '가상제품A', 'confidence': '0.9', 'unit': '정',
             'dose_per_administration': '1', 'ingredients': [
                {'ingredient_name_raw': '가상성분A', 'product_strength': '100',
                 'product_strength_unit': 'mg'}]}]})
        body = {'candidates': [{'content': {'role': 'model', 'parts': [{'text': payload}]},
                                'finishReason': 'STOP'}]}
        with self.transport(200, body), count_analysis_requests() as count:
            result = extract_image_candidates(b'synthetic', 'image/png', self.context)
        self.assertEqual(count[0], 1)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(result[0]['status'], 'SUCCESS')
        self.assertFalse(result[0]['record']['user_confirmed'])
        self.assertEqual(result[0]['record']['ingredients'][0]['product_strength'], '100')
        sent = json.loads(self.calls[0].content)
        self.assertEqual(sent['generationConfig']['responseMimeType'], 'application/json')

    def test_503_never_retries_and_sanitizes_provider_message(self):
        body = {'error': {'code': 503, 'status': 'UNAVAILABLE', 'message': 'private-marker'}}
        with self.transport(503, body), count_analysis_requests() as count:
            result = extract_image_candidates(b'synthetic', 'image/png', self.context)
        self.assertEqual(count[0], 1)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(result[0]['status'], 'FAILED')
        self.assertNotIn('private-marker', json.dumps(result))

    def test_empty_sdk_response_is_failed(self):
        with self.transport(200, {'candidates': []}):
            result = extract_image_candidates(b'synthetic', 'image/png', self.context)
        self.assertEqual(result[0]['status'], 'FAILED')
        self.assertEqual(len(self.calls), 1)

    def test_cli_precheck_never_calls_provider_and_hides_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / 'synthetic.png'
            image.write_bytes(b'synthetic')
            argv = ['--image', str(image), '--synthetic-input', '--family-member-id',
                    self.context.family_member_id, '--source-document-id', 'synthetic',
                    '--record-date', '2026-10-22']
            output = io.StringIO()
            with patch.dict(os.environ, {'GEMINI_API_KEY': 'private-marker',
                                         'YAKEUM_GEMINI_MODEL': 'private-model'}, clear=True):
                with patch('backend.services.extraction.scripts.run_image.extract_image_candidates') as provider:
                    with contextlib.redirect_stdout(output):
                        code = main(argv)
            provider.assert_not_called()
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue())['analysis_requests'], 0)
            self.assertNotIn('private-marker', output.getvalue())
            self.assertNotIn('private-model', output.getvalue())

    def test_cli_requires_synthetic_confirmation(self):
        output = io.StringIO()
        with patch('backend.services.extraction.scripts.run_image.extract_image_candidates') as provider:
            with contextlib.redirect_stdout(output):
                code = main(['--image', 'missing.png', '--family-member-id',
                             self.context.family_member_id, '--source-document-id',
                             'synthetic', '--record-date', '2026-10-22', '--allow-live'])
        provider.assert_not_called()
        self.assertEqual(code, 2)
