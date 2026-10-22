"""Regression tests using synthetic bytes and fake provider responses only."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from . import extraction as ex


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.image = Path(self.temp.name) / 'virtual.png'
        self.image.write_bytes(b'synthetic-image')
        self.payload = json.dumps({'document_type': '약봉투', 'medications': [
            {'name': '가상제품A', 'confidence': None},
            {'name': '가상제품B', 'confidence': '0.8'}]})
        env = patch.dict(os.environ, {'GEMINI_API_KEY': 'fake-key',
                                     'YAKEUM_GEMINI_MODEL': 'fake-model'}, clear=True)
        env.start()
        self.addCleanup(env.stop)

    def test_multiple_products_and_null_confidence(self):
        with patch.object(ex, '_request_image', return_value=self.payload) as request:
            result = ex.extract_medicine_info(self.image)
        request.assert_called_once_with(b'synthetic-image', 'image/png', 'fake-model', 'fake-key')
        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.medications), 2)
        self.assertEqual(result.medications[0].confidence, -1.0)
        self.assertEqual(result.medications[1].confidence, 0.8)

    def test_missing_settings_never_calls_provider(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(ex, '_request_image') as request:
            self.assertIsNotNone(ex.extract_medicine_info(self.image).error_message)
        request.assert_not_called()

    def test_invalid_files_never_call_provider(self):
        empty = Path(self.temp.name) / 'empty.png'
        empty.touch()
        with patch.object(ex, '_request_image') as request:
            for path in (empty, self.image.parent, self.image.with_suffix('.pdf'), None):
                with self.subTest(path=path):
                    self.assertIsNotNone(ex.extract_medicine_info(path).error_message)
        request.assert_not_called()

    def test_provider_failure_is_sanitized_without_fallback(self):
        output = io.StringIO()
        with patch.object(ex, '_request_image', side_effect=RuntimeError('private-marker')) as request:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                result = ex.extract_medicine_info(self.image)
        request.assert_called_once()
        self.assertIsNotNone(result.error_message)
        self.assertNotIn('private-marker', repr(result) + output.getvalue())

    def test_invalid_responses_fail_without_second_request(self):
        payloads = [None, '', 'not json', '[]', '{}',
                    '{"document_type":"약봉투","medications":[]}',
                    '{"document_type":"약봉투","medications":[{"name":null}]}',
                    self.payload.replace('"0.8"', '"NaN"'),
                    self.payload.replace('"0.8"', 'true'),
                    json.dumps(dict(json.loads(self.payload), document_type='unknown'))]
        for payload in payloads:
            with self.subTest(payload=payload), patch.object(ex, '_request_image', return_value=payload) as request:
                result = ex.extract_medicine_info(self.image)
                self.assertIsNotNone(result.error_message)
                self.assertEqual(result.medications, [])
                request.assert_called_once()

    def test_fenced_json_is_supported(self):
        result = ex._parse_response('```json\n' + self.payload + '\n```')
        self.assertEqual(len(result.medications), 2)
