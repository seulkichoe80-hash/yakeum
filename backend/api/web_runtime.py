"""Opt-in same-origin static build for a synthetic-data demo, not production auth."""
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles


def configure_web(app):
    @app.get('/api/health',include_in_schema=False)
    def health():
        # Liveness only: never disclose credentials, paths, account data or API readiness.
        return {'status':'ok','service':'yakeum','scope':'synthetic-demo'}
    if os.environ.get('YAKEUM_SERVE_FRONTEND')=='1':
        directory=Path(os.environ.get('YAKEUM_FRONTEND_DIST',str(Path(__file__).resolve().parents[2]/'frontend/dist')))
        app.mount('/',StaticFiles(directory=directory,html=True,follow_symlink=False),name='frontend-build')
