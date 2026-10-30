"""Loopback browser harness with synthetic-only XML, never deployed."""
import os
from pathlib import Path
if (os.environ.get('YAKEUM_MFDS_MATCH_TEST_TRANSPORT')!='1'
        or os.environ.get('MFDS_API_KEY')!='SYNTHETIC-SECRET'
        or not os.environ.get('YAKEUM_DEV_DB_PATH','').startswith('/tmp/')
        or os.environ.get('YAKEUM_STORAGE_BACKEND','sqlite')!='sqlite'):
    raise RuntimeError('Explicit synthetic test environment required')
from backend.api.main import app
from backend.services.mfds import probe
from backend.tests.test_live_mfds_matching import xml

def fake(key,name,page,rows):
    assert key=='SYNTHETIC-SECRET' and (page,rows)==(1,3)
    counter=Path(os.environ['YAKEUM_MFDS_TEST_COUNTER'])
    counter.write_text(str(int(counter.read_text())+1 if counter.exists() else 1))
    case=Path(os.environ['YAKEUM_MFDS_TEST_CASE']).read_text().strip()
    if case=='error':raise TimeoutError('synthetic')
    return xml(case)
probe.fetch_xml=fake
