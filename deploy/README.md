현재 무료 배포 준비 안내는 [FREE_DEPLOY.md](FREE_DEPLOY.md)를 따릅니다. 아래 SQLite+디스크 구성은 로컬/이전 유료 검토 기록입니다.

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

## 외부 가상 시연 권장 구성

권장: **단일 Docker 컨테이너 + 영속 /data 볼륨 + HTTPS/초대 대상 접근 제한을 제공하는 앞단**.
React 정적 파일과 FastAPI가 같은 Origin을 쓰므로 쿠키/CSRF/CORS 구성이 단순하다.
무료 여부는 미확인이다. 호스팅은 단일 인스턴스와 영속 디스크를 지원하는 상품을 선택해야 한다.
Vercel/GitHub Pages 같은 정적 호스팅만으로는 현재 Python API/SQLite 저장을 제공할 수 없다.
자동 확장·다중 인스턴스·서버리스 임시 디스크는 현재 구성에 적합하지 않다.

외부 게시 전에 사용자가 준비할 것:

1. 컨테이너 호스팅 계정 또는 VM 계정·결제/예산 확인. 현재 실제 서비스 생성/신청하지 않음.
2. 플랫폼 HTTPS 주소(또는 소유 도메인), /data 영속 디스크, 단일 인스턴스/worker 1.
3. 호스팅 앞단의 초대 사용자 접근 제한. 앱의 개발용 가입·로그인은 공개 운영 인증을 대신하지 않음.
4. 가상 자료 전용 안내, 시연 후 가상 계정·자료 삭제/보관 기한 결정. 운영 보관 정책으로 확정한 것이 아님.
5. 외부 공개 별도 승인 후 아래 Origin/Cookie/시연 설정을 지정하고 HTTPS·권한을 실제 검증.

| 환경변수 | 내부 HTTP 예행연습 | 승인 후 외부 HTTPS 가상 시연 |
|---|---|---|
| YAKEUM_EXTERNAL_DEMO | 0 | 1 |
| YAKEUM_APP_MODE | development | development(운영 인증 아님) |
| YAKEUM_SERVE_FRONTEND | 1 | 1 |
| YAKEUM_DEV_ACCOUNT_ENABLED | 1 | 1 |
| YAKEUM_DEV_ORIGIN | 정확한 http://127.0.0.1:포트 | 실제 https://호스트[:포트], 끝 / 없이 |
| YAKEUM_DEV_COOKIE_SECURE | 0 | 1 |
| YAKEUM_DEV_DB_PATH | /data/yakeum.sqlite3 | 영속 /data/yakeum.sqlite3 |
| YAKEUM_GEMINI_LIVE_ENABLED | 0 | 0 |
| YAKEUM_GEMINI_LIVE_MAX_REQUESTS | 1 | 1(비활성 상태의 기본 한도) |

외부 시연 flag=1이면 시작 시 HTTPS Origin·보안 쿠키·위 설정과 소스 밖 DB 경로를 검사한다.
이 검사는 실제 HTTPS 인증서·영속 볼륨·앞단 접근 제어를 만들어 주거나 검증하지 않는다.
/api 응답은 Cache-Control:no-store, 전체 응답에 nosniff/no-referrer를 지정한다.
이미 브라우저/프록시에 저장된 과거 캐시를 소급 삭제하는 기능은 아니다.

SQLite 파일은 암호화된 운영 DB가 아니다. 같은 볼륨이면 재시작 뒤 유지되지만 디스크 삭제 시 사라진다.
현재 scrypt/세션/가족 소유권은 개발용 검사 범위이며 운영 인증·복구·백업 자동화 완료가 아니다.
백업/복원은 docs/integration/DELETION_BACKUP_REVIEW.md의 가상 DB 절차를 사용한다.

### Compose로 내부 예행연습 (외부 공개 없음)

먼저 위 방법으로 `yakeum-synthetic:local` 이미지를 빌드한다.

```bash
docker compose -f deploy/compose.yaml config --quiet
docker compose -f deploy/compose.yaml up -d
curl --fail http://127.0.0.1:8080/api/health
# 종료만: 볼륨을 삭제하는 -v 옵션은 쓰지 않는다.
docker compose -f deploy/compose.yaml down
```

Compose는 loopback 바인딩·비root 이미지·읽기 전용 루트·/tmp 임시 디스크·권한 축소·영속 볼륨을 사용한다.
실제 Gemini/MFDS 키를 빈 값으로 고정하고 호스트의 실제 키를 전달하지 않는다.
실제 Gemini 시험은 이 외부 Mock 시연 구성과 분리해 별도 승인된 단일 프로세스에서만 수행한다.
Compose 변수 YAKEUM_DEMO_PORT를 바꾸면 YAKEUM_DEMO_ORIGIN도 같은 포트로 맞춘다.
YAKEUM_DEMO_IMAGE로 검증한 이미지 태그를 선택할 수 있다.
HTTPS 앞단 연결은 호스팅 환경에 맞게 별도 구성하며 이 파일만 실행해서 공개 링크가 생기지 않는다.

### 외부 공개 직전 체크리스트 (아직 미검증)

- HTTPS 인증서와 정확한 Origin, Secure/HttpOnly/SameSite 쿠키, 앞단 접근 제한 확인.
- 가상 계정만 허용하고 사용자 2명·가족 여러 명의 조회/수정/삭제 권한 확인.
- 사진/HIRA 정상·보류·저장·재조회·삭제 및 재시작 후 복원 확인.
- 업로드 크기/응답 시간/서버 디스크 용량/동시 사용자 제한을 앞단과 함께 확인.
- 앱/프록시/호스팅 로그에 URL query, 쿠키, Authorization, 사진, 약 정보가 남지 않도록 설정·검사.
- SQLite 파일/백업은 공개 경로에 두지 않고 별도 암호화·접근 권한/보관 기간을 결정.
- API 키·실제 데이터 없는 이미지인지 확인. 실제 건강정보 운영 사용은 계속 금지.

현재는 코드/컨테이너의 로컬 예행연습까지만 검증했으며 호스팅 계정·HTTPS·외부 접근은 미검증이다.

## 구체적 호스팅 추천과 외부 입구

[Render 배포 직전 안내·비용 비교·수동 설정](RENDER_PREDEPLOY.md)을 추가했다.
Render 유료 단일 Web Service + 영속 디스크를 추천하지만 공식 가격/Blueprint 스키마 접속이 차단돼
`render.yaml`은 미배포 초안이다. 현재 요금과 UI 검증 후 별도 승인으로만 적용한다.
외부 시연 flag=1에는 이제 YAKEUM_DEMO_GATE_USERNAME과 최소 20자의
YAKEUM_DEMO_GATE_PASSWORD가 필수다. 공유 입구 없이 화면/API/문서를 공개하지 않는다.
/api/health는 최소 liveness만 공개하며 개별 가족 권한을 부여하지 않는다.
Compose 내부 예행연습(flag=0)은 기존대로 동작한다. 외부 flag=1을 Compose에 적용하려면
두 입구 변수를 컨테이너에 별도 전달해야 하므로 기존 파일을 그대로 외부용으로 사용하지 않는다.

### 외부 시연의 승인된 Gemini 합성 검증

일반 `YAKEUM_GEMINI_LIVE_ENABLED=0` 보호는 유지합니다. `1`로 바꾸면 시작이 거부됩니다.
별도 관리자·고정 이미지·PostgreSQL 전역 2슬롯 검증의 설정/클릭/한계는
[RENDER_GEMINI_RESTRICTED.md](../docs/integration/RENDER_GEMINI_RESTRICTED.md)를 따릅니다.
새 설정의 적용과 실제 호출은 별도 승인 후 진행하며 자동 재시도/슬롯 초기화는 하지 않습니다.
