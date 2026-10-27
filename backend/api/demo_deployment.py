"""Fail closed on contradictory external synthetic-demo settings; never call APIs."""
import os
from pathlib import Path
from urllib.parse import urlsplit


def validate_external_demo_settings(values=None):
    values = os.environ if values is None else values
    if values.get('YAKEUM_EXTERNAL_DEMO') != '1':
        return
    required = {
        'YAKEUM_APP_MODE': 'development',
        'YAKEUM_SERVE_FRONTEND': '1',
        'YAKEUM_DEV_ACCOUNT_ENABLED': '1',
        'YAKEUM_DEV_COOKIE_SECURE': '1',
        'YAKEUM_GEMINI_LIVE_ENABLED': '0',
    }
    for name, expected in required.items():
        if values.get(name) != expected:
            raise RuntimeError(f'External synthetic demo requires {name}={expected}.')
    try:
        origin = values.get('YAKEUM_DEV_ORIGIN', '')
        parsed = urlsplit(origin)
        valid = (parsed.scheme == 'https' and parsed.hostname and parsed.port != 0
                 and not parsed.username and not parsed.password and not parsed.path
                 and not parsed.query and not parsed.fragment and '*' not in parsed.netloc
                 and not any(c.isspace() for c in origin))
    except ValueError:
        valid = False
    if not valid:
        raise RuntimeError('External synthetic demo requires one exact HTTPS origin.')
    backend=values.get('YAKEUM_STORAGE_BACKEND','sqlite')
    if backend=='postgres':
        from backend.storage.postgres_db import connection_settings
        try:connection_settings(values)
        except Exception:raise RuntimeError('External synthetic demo PostgreSQL settings are invalid.') from None
    elif backend=='sqlite':
        db = Path(values.get('YAKEUM_DEV_DB_PATH', ''))
        checkout = Path(__file__).resolve().parents[2]
        if not db.is_absolute() or db.resolve().is_relative_to(checkout):
            raise RuntimeError('External synthetic demo database must be an absolute path outside source.')
    else:raise RuntimeError('Unsupported synthetic demo storage backend.')

    username = values.get('YAKEUM_DEMO_GATE_USERNAME', '')
    password = values.get('YAKEUM_DEMO_GATE_PASSWORD', '')
    if not username or ':' in username or len(password) < 20:
        raise RuntimeError('External synthetic demo requires a gate username and a password of at least 20 characters.')
