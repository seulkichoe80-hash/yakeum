# 가상 시연 배포 준비 (운영 배포 아님)

한 컨테이너에서 빌드된 React 화면과 FastAPI를 같은 주소로 제공한다. Vite 개발 서버가 필요 없다.
기본은 Mock, 계정 기능 꺼짐, Gemini 실제 호출 꺼짐. 개발용 계정을 켜도 실제 건강정보를 받지 않는다.

## 로컬/내부 가상 시연

```bash
docker build -t yakeum-synthetic:local .
docker run --name yakeum-synthetic-demo \
  -p 127.0.0.1:8080:8080 \
  --mount type=volume,src=yakeum-synthetic-data,dst=/data \
  -e YAKEUM_DEV_ACCOUNT_ENABLED=1 \
  -e YAKEUM_DEV_ORIGIN=http://127.0.0.1:8080 \
  yakeum-synthetic:local
```

이 주소는 서버 컴퓨터 안에서만 열린다. 클라우드의 사용자 접속 링크가 만들어진 것이 아니다.
운영 배포/외부 공개는 별도 승인과 호스팅·HTTPS·접근 제한 설정을 거친다.
DB 경로 /data/yakeum.sqlite3는 /app 소스 밖이다. UID/GID 10001이 볼륨에 쓸 수 있어야 한다.
볼륨이 없는 임시 컨테이너는 저장의 지속성을 보장하지 않는다. `docker rm -v` 등으로 볼륨을 지우지 않는다.

HTTPS 진입점을 실제로 설정한 뒤에는 정확한 YAKEUM_DEV_ORIGIN=https://...와
YAKEUM_DEV_COOKIE_SECURE=1을 지정한다. 로컬 HTTP에서 이 값을 1로 켜면 브라우저가 세션 쿠키를 보내지 않는다.
이는 개발용 쿠키 옵션이며 운영 인증이 구현된 것은 아니다. YAKEUM_APP_MODE=production의 계정 거부는 유지한다.
실제 키를 Dockerfile/build arg/프론트 환경변수에 넣지 않는다. 런타임 비밀 설정만 사용한다.

## 컨테이너 없이 동일 주소 실행

```bash
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
export YAKEUM_SERVE_FRONTEND=1
# 계정 사용 시 DEV_ACCOUNT_STORAGE_V1.md의 개발용 DB/Origin 설정도 필요
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8080 --no-access-log
```

YAKEUM_FRONTEND_DIST는 선택적 정적 빌드 경로다. 없으면 frontend/dist를 사용하며 빌드가 없으면 시작에 실패한다.
소스 루트나 DB 폴더를 정적 파일 경로로 지정하지 않는다. 기본 static 경로는 빌드 산출물만 제공한다.
/api/health는 최소 liveness이며 DB/키/외부 API 성공을 보장하지 않는다. 키·경로·계정 정보를 반환하지 않는다.
외부 폰트 요청도 제거해 기본 시연 화면은 외부 폰트 서버 없이 작동한다.

## 클라우드 프록시/CA가 필요한 빌드

```bash
# 관리형 클라우드에서만. 기존 registry 자격증명/프록시를 보존한다.
BUILDX_CONFIG=/tmp/yakeum-buildx docker build \
  --secret id=proxy_ca,src="$CODEX_PROXY_CERT" \
  --secret id=system_ca,src=/etc/ssl/certs/ca-certificates.crt \
  -t yakeum-synthetic:local .
```

CA는 BuildKit 임시 mount이며 이미지에 복사하지 않는다. TLS 검증을 끄지 않는다.
기본 이미지 tag와 일부 Python 전이 의존성은 완전 고정 lock이 아니므로 운영용 재현성·보안 점검은 별도다.
테스트한 직접 의존성은 deploy/constraints.txt와 기존 고정 requirements에 명시했다.

## 자동 검사

.github/workflows/mvp-validation.yml은 현재 작업 브랜치 push 또는 수동 실행에서 가상 검사만 수행한다.
API 키/외부 분석/배포 단계는 없다. GitHub 실행 여부·성공은 로컬 통과와 별도 확인해야 한다.
main/develop에 workflow를 복사하거나 병합하지 않는다.
