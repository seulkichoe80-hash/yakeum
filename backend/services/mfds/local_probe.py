"""PC-only private key entry for the unchanged one-request probe."""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import warnings

from . import probe


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check-key', action='store_true', help='Private key input and registration check; NO request')
    mode.add_argument('--live', action='store_true', help='ONE public product request; no retry or next page')
    args = parser.parse_args(argv)
    if not (args.check_key or args.live):
        print(json.dumps({'mode': 'instructions_only', 'request_attempts': 0}))
        parser.print_help()
        return 0
    old = os.environ.get('MFDS_API_KEY')
    try:
        # Refuse getpass's fallback to visible input in unsupported consoles.
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            key = getpass.getpass('MFDS Decoding key (hidden input): ').strip()
        if not key:
            print(json.dumps({'error': 'KEY_MISSING', 'request_attempts': 0}))
            return 1
        os.environ['MFDS_API_KEY'] = key
        print(json.dumps({'probe_sha256': hashlib.sha256(Path(probe.__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()}))
        return probe.main(['--live', '--name', '타이레놀', '--page', '1', '--rows', '3'] if args.live else [])
    except (getpass.GetPassWarning, EOFError):
        print(json.dumps({'error': 'PRIVATE_INPUT_UNAVAILABLE_USE_TERMINAL', 'request_attempts': 0}))
        return 1
    except KeyboardInterrupt:
        print(json.dumps({'error': 'CANCELLED_NO_AUTOMATIC_RETRY'}))
        return 130
    except Exception:
        # Unexpected exceptions must not echo a key from an exception message.
        # A request may already have started; do not claim zero attempts here.
        print(json.dumps({'error': 'LOCAL_EXECUTION_FAILURE', 'automatic_retries': 0}))
        return 1
    finally:
        if old is None:
            os.environ.pop('MFDS_API_KEY', None)
        else:
            os.environ['MFDS_API_KEY'] = old
        # Python cannot promise secure erasure of strings; close this process.
        key = None


if __name__ == '__main__':
    raise SystemExit(main())
