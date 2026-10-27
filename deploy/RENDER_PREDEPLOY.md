# 추천: Render 유료 단일 Docker Web Service + 영속 디스크

외부 공개 전 검토용. 서비스 생성·결제·Blueprint 연결은 아직 하지 않았다.
기존 작업/DB를 옮기거나 실제 API를 활성화하지 않는다. 가상 자료 전용이다.

## 방식 비교와 추천

| 방식 | 저장·HTTPS·접근 제한 | 초보자 난이도 | 잠정 월 예산(USD) |
|---|---|---|---|
| Render 유료 단일 Web Service + disk | /data 디스크, 플랫폼 HTTPS, 이번 공유 비밀번호 입구 + 앱 계정 | 낮음: Git 연결·환경변수·디스크 설정 | $10~20 예산 제안 |
| Railway 컨테이너 + volume | 볼륨·HTTPS, 동일 입구 가능. 사용량 과금/구성 확인 필요 | 보통: 사용량 예산 관리 | $5~20 이상 가변 추정 |
| 소형 VPS + 기존 Compose + HTTPS 프록시 | 디스크 직접 관리, TLS·방화벽·업데이트·복구 직접 담당 | 높음 | $6~15 이상 + 도메인 선택 비용 추정 |

위 금액은 **현재 공식 견적이 아닌 계획용 범위**이며 상한/무료 보장이 아니다.
Render의 과거 Starter $7/월 + 디스크 $0.25/GB·월 기준이면 1GB에서 약 $7.25였으나,
현재 공식 페이지를 열지 못했으므로 현재 요금이라고 사용하지 않는다. 세금·환율·추가 사용량은 별도다.
이번에 https://render.com/pricing 및 https://render.com/docs/blueprint-spec 접속을 시도했으나
프록시 CONNECT 403으로 차단됐다. 최신 플랜 이름/가격/디스크 요금·스냅샷·팀 요금·스키마는 미확인이다.
계정 결제 화면에서 현재 최소 유료 사양/디스크 비용을 확인하고 사용자가 승인하기 전 생성/결제하지 않는다.

현재 구조에는 **Render**를 추천한다. 하나의 주소에 화면/API를 함께 띄우고 HTTPS를 관리해 주며,
VM의 OS/TLS 설정 부담이 줄어든다. 무료 임시 디스크 서비스는 SQLite 보존 요건을 충족한다고 보지 않는다.
정적 웹 호스팅만으로는 이 Python API/DB를 실행할 수 없다. 자동 확장하지 않고 단일 인스턴스를 사용한다.
지역/요금제의 실제 디스크 지원·용량·UID 쓰기 권한은 배포 전에 확인해야 한다.

## 준비한 파일과 동작

- 기존 Dockerfile: frontend 빌드 + backend, port 8080, 단일 uvicorn worker, 비root 10001.
- `deploy/render.yaml`: 수동 설정에 대조할 **미배포 초안**. 외부 스키마 validator는 미실행.
  Git 루트 기준 Dockerfile 경로이며 custom Blueprint path를 지정할 수 있는지 공식 UI에서 확인해야 한다.
  autoDeploy:false는 자동 배포 방지 의도다. 현재 서비스 UI에서 수동 배포 설정을 반드시 재확인한다.
- `YAKEUM_EXTERNAL_DEMO=1`: HTTPS Origin/Secure 쿠키/실제 Gemini 꺼짐/공유 입구 설정이 없으면 시작 거부.
- 공유 입구는 HTTP Basic이다. 화면·정적 파일·API·Swagger/OpenAPI 전부 비밀번호로 차단한다.
  /api/health만 비밀·자료 없는 최소 liveness로 예외 제공. 입구로 가족별 권한을 우회할 수 없다.
- 공유 입구 통과 후 기존 개발용 계정 로그인·가족 소유권·CSRF는 별도로 적용한다.
- 입구는 작은 초대 시험용 공유 비밀번호이지 개별 사용자 초대/운영 인증/시도 제한·감사 시스템이 아니다.
  초대한 사람에게만 전달, 필요 시 교체. 공개 모집/실제 건강정보 사용 금지.
- Basic 인증정보는 브라우저가 보관할 수 있다. 앱 로그아웃은 입구 비밀번호를 지우지 않는다.
  공용 PC 사용 금지. 시연 종료 시 브라우저 세션 종료, 공유 비밀번호 교체/서비스 중지.

## 사용자가 준비할 것 (아직 서비스 생성하지 않기)

1. Render 계정 및 GitHub 저장소 읽기 권한. 프로젝트 저장소를 공개로 바꿀 필요 없다.
2. 현재 유료 서버+디스크 요금/한도 확인, 예산 승인. 결제 정보는 Render에만 입력.
3. 시험자 범위·가상 계정 자료 보관 기간·시연 종료 후 중지 계획.
4. 최소 20자 무작위 입구 비밀번호를 비밀번호 관리자로 생성해 Render secret 환경변수로 입력.
   대화/명령행 인자/저장소에 넣지 않는다. 이 문서에는 실제 입구 아이디/비밀번호가 없다.
5. 기본 onrender.com HTTPS 주소 사용 여부 결정. 사용자 소유 도메인은 선택 사항.

## 별도 배포 승인 후 진행할 절차 (지금 실행하지 않음)

1. Dashboard → 새 Web Service에서 해당 저장소, `codex/mvp-completion`, 검증한 SHA를 선택한다.
2. Docker runtime, 루트 Dockerfile/컨텍스트, 단일 인스턴스, /data 영속 디스크 1GB 이상.
   원하는 지역/사양 지원과 최종 요금을 확인한다. 포트는 컨테이너 8080을 사용한다.
3. 서비스 주소가 정해지면 정확한 Origin `https://실제호스트`를 설정한다(끝 / 없음).
   주소를 모른 채 임의 URL로 성공 처리하지 않는다. 최초 시작이 설정 부족으로 실패하면
   URL을 확인하고 환경변수 수정 후 수동 배포하며 Mock 성공으로 숨기지 않는다.
4. render.yaml의 고정 변수 + 아래 수동 값을 설정한다.

| 수동 변수 | 의미 |
|---|---|
| YAKEUM_DEV_ORIGIN | 실제 Render HTTPS origin |
| YAKEUM_DEMO_GATE_USERNAME | 초대 시험자용 공유 입구 아이디 |
| YAKEUM_DEMO_GATE_PASSWORD | 최소 20자 무작위 값, secret으로 입력 |

고정값: EXTERNAL_DEMO=1, APP_MODE=development, SERVE_FRONTEND=1,
DEV_ACCOUNT_ENABLED=1, DEV_COOKIE_SECURE=1, DEV_DB_PATH=/data/yakeum.sqlite3,
GEMINI_LIVE_ENABLED=0, GEMINI_LIVE_MAX_REQUESTS=1. 모두 YAKEUM_ 접두사 사용.
GEMINI_API_KEY/MFDS_API_KEY는 **비워 둔다**. Render에는 기존 실제 키를 복사하지 않는다.

5. 자동 배포를 끄고 수동 배포만 사용. 예상치 못한 push가 공개 사이트에 자동 반영되지 않게 한다.
6. 아래 승인 후 검증을 모두 마친 뒤에만 시험자에게 주소/입구 자격증명을 별도 안전한 경로로 전달.

## 외부 주소에서 반드시 검증할 것 (아직 미실행)

- 정상 HTTPS 인증서/HTTP→HTTPS, 공유 입구 없는 /·/docs·/api/...가 401, 잘못된 비밀번호 거부.
- 실제 HTTPS에서 Secure/HttpOnly/SameSite 쿠키, Origin/CSRF, 사용자 2명·가족 여러 명의 접근 거부.
- 사진/HIRA Mock 정상·보류·별도 복용·저장·재로그인·삭제·취소/늦은 응답 차단.
- 서비스 재시작/재배포 후 자료 유지와 백업·복원. 디스크 삭제는 자료 삭제이므로 임의 실행 금지.
- 서버 파일/DB가 웹에서 노출되지 않고 호스팅 로그에 쿠키/Authorization/키/사진/약 정보가 없는지 확인.
- 트래픽/동시 사용자/업로드 용량/CPU·메모리 제한. /api/health는 DB/외부 API 성공 지표가 아님.
- Basic 입구 자체에는 시도 제한이 없으므로 작은 초대 시연 외 확장 시 호스팅 앞단 보호를 별도 준비.

Compose는 내부 HTTP 예행연습용 그대로 유지한다. Render는 Compose 파일을 직접 실행하는 방식이 아니다.
실제 TLS 인증서·호스팅 로그인·네트워크 공개·과금 검증은 계정 없이 로컬에서 완료할 수 없다.
현재 시연은 Mock. 이전 Gemini 합성 1회 성공 기록은 일반 사진/현재 배포의 실연동 성공을 뜻하지 않는다.
SQLite와 로그인은 개발용이며 운영 암호화/백업 자동화/계정 복구·삭제 정책 완료가 아니다.
