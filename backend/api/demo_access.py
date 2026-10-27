"""Shared password entrance for a synthetic demo; not patient-data authentication."""
import base64
import binascii
from hmac import compare_digest


def demo_access_allowed(authorization, username, password):
    try:
        scheme, encoded = (authorization or '').split(' ', 1)
        if scheme.lower() != 'basic':
            return False
        decoded = base64.b64decode(encoded, validate=True)
        supplied_user, supplied_password = decoded.split(b':', 1)
        user_ok = compare_digest(supplied_user, username.encode('utf-8'))
        password_ok = compare_digest(supplied_password, password.encode('utf-8'))
        return user_ok and password_ok
    except (ValueError, binascii.Error):
        return False
