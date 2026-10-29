"""Loopback-only browser harness; not copied into deployment images."""
import os
from pathlib import Path

if (os.environ.get('YAKEUM_MFDS_ADMIN_TEST_TRANSPORT')!='1'
        or os.environ.get('MFDS_API_KEY')!='SYNTHETIC-SECRET'
        or os.environ.get('YAKEUM_STORAGE_BACKEND','sqlite')!='sqlite'
        or not os.environ.get('YAKEUM_DEV_DB_PATH','').startswith('/tmp/')):
    raise RuntimeError('Explicit synthetic-only test environment required')

from backend.api.main import app
from backend.services.mfds import probe


def fake(key,name,page,rows):
    assert key=='SYNTHETIC-SECRET' and (name,page,rows)==('타이레놀',1,3)
    # Counter contains only a number, never request/credential details.
    counter=Path(os.environ['YAKEUM_MFDS_TEST_COUNTER'])
    count=int(counter.read_text()) if counter.exists() else 0
    counter.write_text(str(count+1))
    assert count==0, 'Repeated synthetic external request detected'
    return '<response><header><resultCode>00</resultCode></header><body><pageNo>1</pageNo><numOfRows>3</numOfRows><totalCount>7</totalCount><items>'+''.join(
        f'<item><ITEM_SEQ>SYNTHETIC-{i}</ITEM_SEQ><ITEM_NAME>가상제품{i}</ITEM_NAME><MAIN_ITEM_INGR>[SYNTHETIC]가상성분</MAIN_ITEM_INGR><EDI_CODE/></item>' for i in range(3))+'</items></body></response>'

probe.fetch_xml=fake
