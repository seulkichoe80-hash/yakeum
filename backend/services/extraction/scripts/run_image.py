"""Manual synthetic-image validation; no request unless --allow-live is given."""
import argparse
import json
import os
from pathlib import Path
import sys

from backend.api.extraction_provider import (
    IMAGE_MIME_TYPES, MAX_IMAGE_BYTES, extract_image_candidates,
)
from backend.services.extraction import ExtractionContext, GeminiSettings
from backend.services.extraction.adapter import _validate_context


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--env-file', type=Path, help='Explicit local dotenv path; never auto-loaded')
    parser.add_argument('--family-member-id', required=True)
    parser.add_argument('--source-document-id', required=True)
    parser.add_argument('--record-date', required=True)
    parser.add_argument('--synthetic-input', action='store_true',
                        help='Confirm input is synthetic and contains no personal data')
    parser.add_argument('--allow-live', action='store_true',
                        help='Permit a maximum of one analysis request, no retries')
    args = parser.parse_args(argv)
    context = ExtractionContext(args.family_member_id, args.source_document_id, args.record_date)
    try:
        _validate_context(context)
        if not args.synthetic_input:
            raise ValueError('Synthetic input confirmation required')
        mime = {'.png': 'image/png', '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg', '.webp': 'image/webp'}.get(args.image.suffix.lower())
        if mime not in IMAGE_MIME_TYPES or not args.image.is_file():
            raise ValueError('Unsupported input')
        if not 0 < args.image.stat().st_size <= MAX_IMAGE_BYTES:
            raise ValueError('Invalid input size')
        with args.image.open('rb') as source:
            data = source.read(MAX_IMAGE_BYTES + 1)
        if not 0 < len(data) <= MAX_IMAGE_BYTES:
            raise ValueError('Invalid input size')
    except (ValueError, TypeError, OSError, AttributeError):
        print(json.dumps({'status': 'FAILED', 'analysis_requests': 0,
                          'message': 'Check synthetic image, size and caller context.'}))
        return 2
    if args.env_file is not None:
        try:
            from dotenv import load_dotenv
            if not args.env_file.is_file():
                raise ValueError('Missing env file')
            load_dotenv(args.env_file, override=False, interpolate=False)
        except Exception:
            print(json.dumps({'status': 'FAILED', 'analysis_requests': 0,
                              'message': 'Cannot load explicit local env file.'}))
            return 2
    present = {name: bool(os.environ.get(name, '').strip())
               for name in ('GEMINI_API_KEY', 'YAKEUM_GEMINI_MODEL')}
    if not args.allow_live:
        print(json.dumps({'status': 'PRECHECK', 'analysis_requests': 0,
                          'model_list_requests': 0, 'size_bytes': len(data),
                          'mime_type': mime, 'settings_present': present}))
        return 0 if all(present.values()) else 2
    if not all(present.values()):
        print(json.dumps({'status': 'FAILED', 'analysis_requests': 0,
                          'settings_present': present}))
        return 2
    try:
        from google import genai
        from google.genai import types
        GeminiSettings.from_environment()
        types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1))
    except Exception:
        print(json.dumps({'status': 'FAILED', 'analysis_requests': 0,
                          'message': 'Check SDK installation and configuration.'}))
        return 2
    from backend.services.extraction.sdk import count_analysis_requests
    with count_analysis_requests() as requests:
        results = extract_image_candidates(data, mime, context)
    candidates = []
    for result in results:
        record = result['record']
        candidates.append({
            'status': result['status'],
            'product_name_raw': record['product_name_raw'] if record else None,
            'ingredients': record['ingredients'] if record else [],
            'unit': record['unit'] if record else None,
            'dose_per_administration': record['dose_per_administration'] if record else None,
            'administrations_per_day': record['administrations_per_day'] if record else None,
            'duration_days': record['duration_days'] if record else None,
            'source_type': record['source_type'] if record else None,
            'official_ids_absent': (record['mfds_product_id'] is None and all(
                i['official_ingredient_id'] is None for i in record['ingredients'])) if record else True,
            'confidence': record['confidence'] if record else None,
            'user_confirmed': record['user_confirmed'] if record else False,
            'missing_fields': [item['field'] for item in result['warnings']],
            'errors': result['errors'],
        })
    print(json.dumps({'analysis_requests': requests[0], 'model_list_requests': 0,
                      'candidate_count': sum(r['record'] is not None for r in results),
                      'results': candidates}, ensure_ascii=False, indent=2))
    return 1 if any(r['status'] == 'FAILED' for r in results) else 0


if __name__ == '__main__':
    sys.exit(main())
