"""Explicit offline browser harness; all Google SDK HTTP goes to MockTransport."""
import json
import os
from pathlib import Path
import httpx
from google import genai
from backend.api.main import app
from backend.api import photo_demo

if os.environ.get('YAKEUM_GEMINI_TEST_TRANSPORT')!='1':
    raise RuntimeError('This harness requires explicit offline-test configuration.')
_real_client=genai.Client


def handler(request):
    assert request.url.path.endswith(':generateContent')
    path=Path(os.environ['YAKEUM_GEMINI_FAKE_SCENARIO'])
    scenario=path.read_text().strip()
    with path.with_suffix('.calls').open('a') as log:log.write('fake-generate-content\n')
    if scenario=='timeout':raise httpx.ReadTimeout('synthetic timeout',request=request)
    if scenario=='error':return httpx.Response(503,json={'error':{'code':503,'status':'UNAVAILABLE','message':'synthetic error'}})
    data=json.loads(photo_demo._fixture('single'))
    if scenario=='mixed':data['medications'].append({**data['medications'][0],'dose_per_administration':'읽기불가'})
    raw='invalid-json' if scenario=='bad-json' else json.dumps(data)
    return httpx.Response(200,json={'candidates':[{'content':{'role':'model','parts':[{'text':raw}]},'finishReason':'STOP'}]})


def client(*args,**kwargs):
    options=kwargs['http_options']
    options.client_args.update(transport=httpx.MockTransport(handler),trust_env=False)
    return _real_client(*args,**kwargs)


genai.Client=client
