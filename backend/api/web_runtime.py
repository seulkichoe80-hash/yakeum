"""Opt-in same-origin static build for a synthetic-data demo, not production auth."""
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles


def configure_web(app):
    from backend.api.demo_deployment import validate_external_demo_settings
    validate_external_demo_settings()

    @app.middleware('http')
    async def private_response_headers(request, call_next):
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/api/health',include_in_schema=False)
    def health():
        # Liveness only: never disclose credentials, paths, account data or API readiness.
        return {'status':'ok','service':'yakeum','scope':'synthetic-demo'}
    if os.environ.get('YAKEUM_SERVE_FRONTEND')=='1':
        directory=Path(os.environ.get('YAKEUM_FRONTEND_DIST',str(Path(__file__).resolve().parents[2]/'frontend/dist')))
        app.mount('/',StaticFiles(directory=directory,html=True,follow_symlink=False),name='frontend-build')
