"""Opt-in same-origin static build for a synthetic-data demo, not production auth."""
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from backend.api.demo_access import demo_access_allowed


def configure_web(app):
    from backend.api.demo_deployment import validate_external_demo_settings
    validate_external_demo_settings()

    external_demo = os.environ.get('YAKEUM_EXTERNAL_DEMO') == '1'
    gate_user = os.environ.get('YAKEUM_DEMO_GATE_USERNAME', '')
    gate_password = os.environ.get('YAKEUM_DEMO_GATE_PASSWORD', '')

    @app.middleware('http')
    async def private_response_headers(request, call_next):
        if (external_demo and request.url.path != '/api/health'
                and not demo_access_allowed(request.headers.get('authorization'), gate_user, gate_password)):
            response = JSONResponse({'detail': '가상 시연 접근 비밀번호가 필요합니다.'}, status_code=401,
                                    headers={'WWW-Authenticate': 'Basic realm="YAKEUM synthetic demo", charset="UTF-8"',
                                             'Cache-Control': 'no-store'})
        else:
            response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        if external_demo or request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/api/health',include_in_schema=False)
    def health():
        # Liveness only: never disclose credentials, paths, account data or API readiness.
        return {'status':'ok','service':'yakeum','scope':'synthetic-demo'}
    if os.environ.get('YAKEUM_SERVE_FRONTEND')=='1':
        directory=Path(os.environ.get('YAKEUM_FRONTEND_DIST',str(Path(__file__).resolve().parents[2]/'frontend/dist')))
        app.mount('/',StaticFiles(directory=directory,html=True,follow_symlink=False),name='frontend-build')
