# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim AS web
WORKDIR /build
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca; fi; \
    npm install --global pnpm@11.25.0 && pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12-slim-bookworm AS app
WORKDIR /app
COPY backend/requirements.txt /deps/backend/requirements.txt
COPY backend/services/normalization/requirements.txt /deps/backend/services/normalization/requirements.txt
COPY backend/services/extraction/requirements.txt /deps/backend/services/extraction/requirements.txt
COPY deploy/constraints.txt /deps/constraints.txt
RUN --mount=type=secret,id=system_ca \
    if [ -f /run/secrets/system_ca ]; then export PIP_CERT=/run/secrets/system_ca; fi; \
    python -m pip install --no-cache-dir -c /deps/constraints.txt -r /deps/backend/requirements.txt
COPY backend/api/ /app/backend/api/
COPY backend/services/ /app/backend/services/
COPY backend/storage/ /app/backend/storage/
COPY --from=web /build/dist /app/frontend/dist
RUN chmod -R a+rX,go-w /app/backend /app/frontend \
    && groupadd --gid 10001 yakeum && useradd --uid 10001 --gid 10001 --no-create-home yakeum \
    && mkdir /data && chown yakeum:yakeum /data
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    YAKEUM_SERVE_FRONTEND=1 YAKEUM_APP_MODE=development \
    YAKEUM_DEV_ACCOUNT_ENABLED=0 YAKEUM_GEMINI_LIVE_ENABLED=0 \
    YAKEUM_GEMINI_LIVE_MAX_REQUESTS=1 YAKEUM_DEV_DB_PATH=/data/yakeum.sqlite3
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=3).read()"
CMD ["python", "-m", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--no-access-log"]
