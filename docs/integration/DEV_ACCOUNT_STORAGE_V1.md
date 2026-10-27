# 개발용 로그인·가족 구분·저장 v1

2026-10-27. 작업 브랜치 codex/mvp-completion.
시작 HEAD `870c0291f751c6869fd2b18f75dc3fe32507d579`, 작업 트리 clean.
명시적 전체 원격 fetch 후 새 팀원 변경 없음. 이전 HEAD로 되돌리거나 다른 브랜치를 수정하지 않았다.

## 무엇이 달라졌나

첫 화면 상단 **개발용 로그인·저장 열기**에서 가상 계정으로 가입/로그인한다.
서버가 현재 로그인 계정의 가족만 보여 주며 가족과 자료 ID를 바꿔 요청해도 소유권을 검사한다.
기존 화면의 Mock 가족·동의 스위치는 실제 권한이 아니다. 개발용 계정 화면과 명확히 분리했다.

사진 두 장 선택 → 가짜 추출 → 후보 수정·대조 확인 → 정규화 검토 → 비교 →
**확인한 결과와 복용 선택 저장** → **저장 목록 새로고침** → 저장 결과 선택.
복용 여부를 아직 선택하지 않았다면 UNKNOWN/PENDING(잘 모르겠음/확인 전) 그대로 저장한다.
다시 로그인하거나 새로고침해도 같은 DB 파일이 있으면 저장 목록을 조회할 수 있다.
저장 결과에서 실제 복용 여부를 별도로 변경할 수 있다. 비교 판정/원본은 바뀌지 않는다.

기존 사진 Mock·비로그인 합성 이미지 업로드·HIRA 비교는 그대로다.
이전 시연 경로는 DB 계정 자료를 읽지 못하며 계속 가상 자료만 처리한다.
**HIRA 결과의 계정별 저장 UI는 이번에 추가하지 않았다.** 기존 HIRA 비교 흐름은 유지한다.
실제 Gemini/MFDS 호출/실제 사진 인식/운영 배포는 실행하지 않았다.

## 실행 설정 — 개발 전용

기본값은 계정 기능 꺼짐이다. 외부 계정·API 키·서명 비밀키는 필요 없다.
기존 설치 절차와 requirements는 그대로 사용한다(Python 환경에 backend/requirements.txt 설치).
아래는 저장소 루트에서 실행하는 Bash 예시다.

```bash
export YAKEUM_DEV_ACCOUNT_ENABLED=1
export YAKEUM_APP_MODE=development
export YAKEUM_DEV_DB_PATH=/workspace/.local/yakeum/accounts.sqlite3
export YAKEUM_DEV_ORIGIN=http://127.0.0.1:4192
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --no-access-log
# 다른 터미널
pnpm --dir frontend dev --port 4192 --strictPort
```

- DB 경로는 소스 저장소 밖의 절대 경로를 명시한다. 저장소 내부 경로는 서버가 거부한다. 예시 위치는 저장소 밖이며 실제 환경에 맞춰 바꾼다.
- YAKEUM_DEV_ORIGIN은 브라우저의 정확한 scheme/host/port 하나다. localhost와 127.0.0.1은 다르다.
- YAKEUM_APP_MODE=production이면 계정 API는 503으로 거부한다. 이것은 운영 모드 구현이 아니다.
- 설정 미완료/꺼짐이면 화면에 오류를 표시하며 자동 임시 로그인·암묵적 DB 생성은 하지 않는다.
- 개발 계정 아이디: 영문 소문자/숫자/_/- 3~40자. 비밀번호: 12~128자.
  평소 쓰는 비밀번호·실제 가족 이름·건강정보 대신 가상 값만 사용한다.
- 프로세스 재시작과 클라우드 환경 삭제는 다르다. DB 파일이 유지되면 재시작 후 읽지만,
  /tmp 또는 클라우드 임시 디스크가 사라지면 복구되지 않는다. 백업/운영 볼륨은 미구현이다.
- 테스트 DB·이미지·세션 자료는 /tmp 또는 pytest 임시 폴더에만 만들고 Git에 넣지 않았다.
  .gitignore에 SQLite 파일/sidecar/.local도 추가했다. 실제 DB를 Git으로 공유하지 않는다.

## 인증·권한 처리

- 비밀번호는 사용자마다 무작위 salt + 표준 라이브러리 scrypt(N=16384,r=8,p=1) 해시로 저장.
- 무작위 256bit 세션 token을 HttpOnly/SameSite=Strict 쿠키에 저장하고 DB에는 SHA-256 hash만 저장.
- 세션은 8시간 절대 만료. 로그인 때 이전 쿠키 세션을 교체하며 로그아웃은 서버 세션을 삭제한다.
- 쿠키는 `/api/dev-account` 경로에만 전달된다. localStorage에 비밀번호/세션/약 자료를 넣지 않는다.
- 개발 HTTP이므로 Secure=false다. **운영용 HTTPS 쿠키 설정으로 오해하지 않는다.**
- 모든 변경 요청에 정확한 Origin 검사. 로그인 후에는 세션별 CSRF token 헤더도 필요하다.
  가입/로그인은 Origin 검사를 받으며 CORS 공개를 추가하지 않았다.
- 로그인/가입은 클라이언트 IP별 10분당 각각 10회 제한. 계정 열거/오류에 비밀번호를 반사하지 않는다.
  reverse proxy 환경·고도화된 공격 방어·이메일 확인·비밀번호 복구·MFA는 미구현이다.
- 가족 owner_id, 자료 family_id는 서버가 지정한다. 다른 사용자 가족은 404, 잘못된 가족의 문서는 410.
  같은 사용자의 가족끼리도 문서/run을 바꿔 끼울 수 없다.
- 모든 보호된 endpoint에 세션/소유권 검사를 적용한다. 로그아웃/만료 후에는 401.
- 계정 API 응답은 Cache-Control:no-store. 잘못된 입력 오류에 비밀번호나 원본 입력을 되돌려주지 않는다.
- 화면 가족 전환은 하위 상태를 새로 만들며 진행 요청을 abort/세대 번호로 무효화한다.
  로그아웃·401은 계정 작업 화면을 제거해 이전 결과와 늦은 응답이 나타나지 않는다.

## 저장 구분과 정책

SQLite schema version 1, 외래 키 사용, 요청별 transaction, DB 권한 0600/새 디렉터리 0700.
지원하지 않는 DB 버전은 보존한 채 503으로 거부하며 임의 초기화하지 않는다.
테이블 생성은 재실행 가능하다. 이후 schema 변경 시 migration을 추가해야 한다.

| 구분 | 보존하는 내용 |
|---|---|
| users / sessions | 계정 ID·해시 / 해시 세션·CSRF·만료 |
| families | 서버 생성 가족 ID·소유자·표시 이름 |
| documents | 서버 문서 ID·가족·기준일/유형·추출 원본. 원본 user_confirmed=false |
| runs.reviews | 후보별 순번·수정 초안·확인 bool, 정규화 최종 확인 bool |
| runs.result | 원본/수정/정규화 snapshot·비교·보류 사유. 처리 시점 복용 초기 상태는 UNKNOWN/PENDING |
| runs.saved | 명시적으로 저장한 비교 결과 표시. 보류/미확인 미리보기는 saved=1 불가 |
| intake | run/record별 실제 복용 확인. 서버가 로그인 사용자 ID와 UTC 확인 시각을 부여 |

사진 bytes·파일명은 DB에 넣지 않고 요청 종료 시 닫는다.
추출 후보 문서는 15분 유효하며 만료 정리는 다음 업로드 시 수행한다.
저장하지 않은 처리 결과는 24시간 후 다음 처리 요청에서 정리한다. 초안은 저장 목록에 표시하지 않는다.
원본 후보·미확인 자료가 DB에 존재한다는 것과 사용자 확인 완료/복용 확인은 다르다.
명시적 저장은 compared 결과만 허용하고, 결과 전체를 클라이언트가 위조해 제출하는 API는 만들지 않았다.
비교 결과는 서버가 원본 문서와 사용자 검토 요청으로 계산한 snapshot에서만 저장한다.
저장 결과에는 필요한 원본/수정/정규화 사본이 있으므로 임시 document 만료 후에도 조회 가능하다.

같은 run을 다시 저장해도 목록을 중복 생성하지 않는다. 명시적으로 전달한 복용 선택만 반영한다.
실제 복용 UNKNOWN을 명시적으로 선택하면 USER_VERIFIED이며, 선택하지 않은 UNKNOWN/PENDING과 구분한다.
실패 후보가 섞이면 정상 후보는 보존하지만 전체 비교 보류. 자동 대표 선택·기록 삭제·정보 추정 없음.

저장은 개발용 파일 지속성만 제공한다. 디스크 암호화/백업/사용자 삭제/보관 동의/보존기간 확정/
물리적 안전 삭제/계정 공유·초대·가족 구성원별 권한은 별도 운영 준비가 필요하다.
원본 DB를 임의 삭제해 초기화하는 대신 경로 변경 또는 안전한 백업을 먼저 검토한다.

## API 추가 계약

공통 MedicationRecord, ExtractionResult, NormalizationResult, Reconciliation 상태/reason_code,
기존 사진/HIRA 입력·응답은 변경하지 않는다. 별도 `/api/dev-account`와 `DEV_ACCOUNT_V1` envelope 추가.
서버 내부 photo_demo 처리 함수를 재사용하며 공통 약 정보에 owner/session 필드를 끼워 넣지 않는다.

| Method / path (접두사 /api/dev-account) | 역할 |
|---|---|
| POST /register, /login | 가상 계정 생성 / 세션 생성 |
| GET /me, POST /logout | 세션 복원·CSRF / 세션 폐기 |
| GET/POST /families | 본인 가족 조회/추가 |
| POST /families/{family}/photos/extract | 보호된 multipart 업로드, 가짜 추출, 원본 후보 보관 |
| POST /families/{family}/photos/process | previous/current document_id + reviews + normalization_confirmed, 서버 비교 snapshot |
| POST /families/{family}/runs/{run}/save | intake_confirmations=[{record_id,choice}] (빈 배열 가능), 확인한 결과 저장 |
| GET /families/{family}/runs | 명시적으로 저장한 목록 |
| GET /families/{family}/runs/{run} | reviews, result(원본/수정/정규화/비교), intake_states 별도 반환 |
| PATCH /families/{family}/runs/{run}/intake | {record_id,choice:TAKING/NOT_TAKING/UNKNOWN} 별도 복용 확인 |

로그인 응답은 {username,csrf_token,development_only:true,response_version:DEV_ACCOUNT_V1}.
extract 응답은 {document_id,results,development_only:true,response_version:DEV_ACCOUNT_V1}.
process 응답은 {run_id,result,development_only:true,response_version:DEV_ACCOUNT_V1}.
result는 기존 사진 처리 결과 의미를 유지하며 여기의 persisted=false는 순수 처리 결과다.
DB 초안 보관/명시적 저장 여부는 계정 envelope·save/list에서 별도로 구분한다.
성공/오류 자체가 실제 AI/공식 데이터 확인을 뜻하지 않는다.

## 아직 운영 준비가 아닌 이유

- 개발용 가입·단일 소유자 가족 모델. 외부 인증 연동·이메일 확인/복구·권한 위임 없음.
- HTTP 개발 쿠키, 로컬 단일 SQLite, 백업·암호화·보관/삭제 정책·운영 모니터링 없음.
- 실제 건강정보 보호 설계와 사용자 동의/접근 정책 검토 미완료. 가상 자료만 사용.
- 기존 비로그인 경로는 합성 시연 전용이며 운영 공개 전 차단/분리 검토가 필요하다.
- 실제 Gemini/MFDS와 HIRA export·운영 배포는 미검증. 이번 외부 서비스 호출 0회.
- 다음 우선순위: 사용자 테스트 → 계정/가족 정책·삭제/백업·배포 설정 검토 → 별도 승인된 실제 연동 검증.

## 실제 실행한 최종 검사

- 백엔드 전체 **306 passed**, 내부 subtest 5 passed. subtest는 독립 검사 수에 더하지 않는다.
  실패/xfail 0, 기존 Starlette deprecation 경고 1개. 새 계정/저장 검사 21개 포함.
- 프론트 기존 7 script 그룹, strict TypeScript, Vite build 통과(46 modules).
- 새 계정·저장 브라우저 **7개 그룹 통과**: 가입/로그인/본인 가족 저장·원본 구분,
  별도 복용 확인, 페이지 재접속, 가족 전환·늦은 응답, 다른 계정 조회·수정 404,
  로그아웃 후 401·늦은 응답 제거, 재로그인 후 저장 결과 복원.
- 기존 사진 업로드 브라우저 **10개 그룹**, 사진 Mock/HIRA **13개 그룹** 통과.
  정상·혼합 실패·미확인/반복 보류·재처리·취소·가족/파일 변경·늦은 응답 차단 유지.
- 360/390/768/1280px 가로 넘침 없음, browser runtime errors 0, 실제 외부 의료 API 요청 0.
- 새 Python 프로세스가 같은 SQLite 파일에서 저장 원본/수정값을 읽는 검사 통과.
  DB 파일 권한·지원하지 않는 schema 버전 거부·세션 교체/만료·CSRF·Origin·시도 제한도 검사.
- 실제 화면 캡처는 /tmp에서 확인했고 Git에 넣지 않았다. pip check와 git diff --check 통과.
- 최종 브라우저는 최신 코드의 격리 backend 8031 / Vite 4198에서 실행했다.
  계정 QA DB는 /tmp/yakeum-account-final/accounts.sqlite3, 기존 실행 프로세스와 코드 보존.

```bash
# 저장소 루트, 프로젝트 Python 환경
python -m pytest backend -q
python -m pip check
pnpm --dir frontend test
pnpm --dir frontend build

# 최신 앱/DB 설정으로 서버를 켠 뒤 실제 환경 경로에 맞게 지정
export YAKEUM_TEST_URL=http://127.0.0.1:4198/
export YAKEUM_TEST_PYTHON=/tmp/yakeum-task-a-venv/bin/python
export YAKEUM_BROWSER_EXECUTABLE=/usr/bin/chromium
export YAKEUM_PLAYWRIGHT_MODULE=/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright
node frontend/tests/account-storage.browser.cjs
node frontend/tests/photo-upload.browser.cjs
node frontend/tests/photo-hira-integration.browser.cjs
```

브라우저 계정 검사는 매번 새 가상 아이디를 만들며 개발 DB에 가상 자료를 남긴다.
로그인 시도 제한도 실제 적용되므로 같은 QA 서버에서 반복 실행하다 제한에 걸리면
제한을 낮추지 말고 대기하거나 별도의 테스트 DB/프로세스로 검사한다.
실제 운영 인증/클라우드 볼륨 지속성/백업 복구/실사용 건강정보/실제 외부 API/운영 배포는
검증하지 않았으며 이번 완료 판정에 포함하지 않는다.
