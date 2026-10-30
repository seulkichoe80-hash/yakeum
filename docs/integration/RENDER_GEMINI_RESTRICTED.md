# Render 관리자 합성 Gemini 검증 — 제한된 별도 승인 경로

2026-10-30. 시작 a9b0f8e. 이번 실제 API 호출/Render 설정 변경/배포 없음.
이 문서는 이전 RENDER_GEMINI_VALIDATION_PLAN.md의 외부 시연 설정 방법을 정정한다.
외부 시연에서 일반 `YAKEUM_GEMINI_LIVE_ENABLED=1`은 허용하지 않는다.
시작 오류는 보호 규칙의 정상 작동이며 보호 규칙을 없애지 않았다.

## 범위와 계약

기존 로그인/가족 소유권/Origin/CSRF/HTTPS 쿠키/입구 비밀번호 검사 유지.
기존 보호된 사진 endpoint에 선택적 multipart `synthetic_consent`와
`synthetic_side`(previous/current)를 추가했다. 공통 ExtractionResult/MedicationRecord,
비교/저장 계약 의미는 그대로다. 기존 로컬 일반 Gemini 경로와 Mock은 유지한다.
외부 시연의 Gemini endpoint는 관리자 합성 검증으로만 진입한다. 일반 사용자에게 체크박스가
보여도 서버가 권한을 검사해 거부한다. 체크만으로 관리자 권한을 얻을 수 없다.

- 서버 지정 기존 계정만 허용. 키는 Render GEMINI_API_KEY만 사용, 클라이언트 입력 없음.
- 명시적 동의, 슬롯(previous/current), image/png 및 SHA-256 정확 일치가 필수.
- 허용 파일: [원본 합성 PNG](samples/render-gemini/synthetic-bag.png).
  c70bba4ae9c8f1ba2e671544dd7b5f76b4ec3d17a81b644ed81263dca7e55060.
  이름 변경은 가능하지만 편집/재저장/압축하면 거부한다. 실제 사진은 거부한다.
- DB `gemini_synthetic_attempts` 고정 전역 슬롯 render-synthetic-bag-v1:previous/current,
  각각 1회, 총 최대 2회. 사용자/가족/날짜/배포 버전/프로세스마다 예산을 새로 만들지 않는다.
- PostgreSQL advisory transaction lock/기본키로 동시 실행 직렬화. I/O 전에 소비 기록 commit.
  실패/시간초과/취소/프로세스 중단/결과 불명확도 소비. 중복 요청은 409, 자동 재호출 없음.
  슬롯 초기화/삭제/재설정 API는 없다. 기존 관리자 MFDS 실행 기록은 건드리지 않는다.
- SDK 기존 60초 I/O 제한, HTTP 시작 최대 1회, 자동 재시도 0.
  취소는 늦은 화면 갱신을 막지만 이미 시작한 과금 요청을 되돌리지 못한다.
- finished는 함수가 반환됐다는 뜻이며 성공 인증이 아니다. 후보 응답의 status/errors로 결과를 본다.
  완료 기록/화면 전송이 실패해도 재호출하지 않는다. 임시 사진 후보는 기존 15분 TTL이며
  DB 소비 기록은 영구 차단 상태로 남는다. 소비 기록에는 키/사진/약 정보/원문이 없다.
- 의약품 매칭은 별개다. 이번 계획은 실제 식약처 체크 해제, 가상알파정 Mock 정규화.
  AI 출처 이전/현재 Gemini 추출 + 가상 의약품 매칭을 화면/저장 결과에서 구분한다.

## 사용자가 승인 후 할 설정 (이번에 적용하지 않음)

Render → 서비스 → Environment. 기존 DB/SSL/쿠키/접근 비밀번호/MFDS/Gemini 키 설정 보존.

1. `YAKEUM_GEMINI_LIVE_ENABLED=0` 유지. **1로 바꾸지 않는다.**
2. `YAKEUM_GEMINI_SYNTHETIC_ENABLED=1`은 별도 실행 승인 후 설정.
3. `YAKEUM_GEMINI_SYNTHETIC_ADMIN_USERNAME`에 기존 관리자 계정 아이디 지정.
   새 계정을 임의로 등록해 권한을 얻는 구조가 아니므로 서버 설정자는 기존 소유 계정을 확인한다.
4. `GEMINI_API_KEY` 비공개 서버 값과 `YAKEUM_GEMINI_MODEL` 확인.
   기존 성공 기록 후보 gemini-3.5-flash-lite의 현재 계정 권한/요금은 별도 확인 필요, 모델 조회 안 함.
5. `YAKEUM_STORAGE_BACKEND=postgres`, 기존 영속 DB 연결/verify-full 설정 유지.
   외부 검증은 SQLite에서 시작할 수 없다. 이 경로는 일반 LIVE_MAX_REQUESTS와 별개로 **DB 최대2회**다.
6. 검증된 SHA 배포는 별도 승인 후. 설정을 지금 바꾸거나 재배포하지 않았다.

## 승인 후 클릭 순서

1. 관리자 로그인 → 가상 가족 선택 → 실제 식약처 체크 **해제**.
2. 현재 사진 및 이전 사진 모두 원본 합성 PNG 선택. 기준일 이전2026-09-01/현재2026-10-01,
   자료 유형 약봉투. 추출 방식 Gemini.
3. **관리자 합성 검증** 동의 체크. 체크 변경은 이전 후보를 초기화하므로 추출 전에 설정한다.
4. 이전 `Gemini로 사진 추출 요청` 1회. 후보 기대값 대조. 실패/불명확하면 중단.
5. 성공 후 현재 동일 버튼 1회. 기대값 가상알파정/가상알파성분/100mg/1회2정/하루2회/7일.
6. 후보 수정 필요 시 수정 후 내용 확인 → B 미리보기 → D 비교. 같은 내용은 기록 동일,
   필수값 미확인/실패는 보류. 추측으로 값을 채우지 않는다.
7. 실제 복용 여부 별도 확인 → 저장 → 목록 새로고침 → 재조회/변경 이력/출처 확인.

총 Gemini 최대2회, 식약처0회, 모델조회0회. 첫 요청 실패 시 1회에서 중단한다.
오류 시 재시도 버튼이 보여도 누르지 않는다. 같은 슬롯은 서버가 차단한다.
페이지 새로고침/다른 가족/재시작으로 추가 예산을 얻을 수 없다.
기존 슬롯이 이미 소비됐다면 재시험은 현재 범위 밖의 새로운 승인·설계 검토가 필요하다.

## 검증 기록

아래 실제 실행 결과를 참조. 실제 Render 적용·실제 모델 권한/가격·실제 Gemini 인식은 미검증.
개발용 인증/저장 환경이며 실제 건강정보 사용을 승인하는 기능이 아니다.

### 실행 결과

- 백엔드 전체 `python -m pytest backend -q`: **549 passed, 42 skipped, 5 subtests passed**.
  미설정 PostgreSQL 항목 42개는 이후 별도 실행하여 **42 passed**.
- 전체 실행 뒤 보강한 3개 검사(미인증/설정 누락, commit 실패 전송 차단, 새 Python 프로세스에서 재사용 차단)를
  포함해 `test_gemini_synthetic.py` **9 passed**. 독립 수를 중복 합산하지 않는다.
- 신규 검사: 동시 요청 중 1개만 가짜 provider 진입, 실패/시간초과/프로세스 중단 영구 소비,
  서로 다른 가족에서도 슬롯 재사용 불가, 관리자/동의/해시/CSRF/가족 권한/키 누락 차단.
- PostgreSQL 가상 DB(loopback, 임시 yakeum_synthetic)에서도 동시 요청/영속 슬롯 검사 통과.
  기존 운영 Supabase는 연결/초기화/삭제하지 않았다.
- 프론트 `pnpm --dir frontend test` 10개 스크립트, TypeScript/Vite 53 modules 통과.
- `gemini-synthetic.browser.cjs`: 원본 합성 PNG와 명시적 동의 → 가짜 SDK 2회 → 후보 확인 →
  정규화/비교 → 저장/재조회 → 같은 슬롯 재호출 409 통과. 출처 분리, 360/390/412/1280px
  가로 넘침 없음, 브라우저 오류0. 실제 Gemini/MFDS 호출0.
- Dockerfile 그대로 실제 이미지 build 성공. 이미지 f1d3cbde5ecdea43f86f6925d62ea0d518fa1ecc17b24f6692d98b33a6cb0a44.
  외부 시연+새 검증 flag+가상 PostgreSQL 설정으로 **기본 CMD 앱 시작 및 health200** 확인.
  `--network none`으로 실제 외부 통신 차단. 이 검사는 실DB 연결/인증/HTTPS 종단 검증이 아니다.
- 같은 Docker 이미지에서 일반 LIVE_ENABLED=1은 기존 오류로 시작 거부,
  새 검증 활성화+SQLite는 시작 거부. 보안 쿠키/HTTPS/입구 보호 설정은 유지했다.
- Docker 최초 빌드는 읽기 전용 기본 buildx 작업 폴더로 실패했다. Docker 인증 설정을 유지하고
  BUILDX_CONFIG만 /tmp로 지정해 빌드했다. 프록시 CA를 BuildKit secret mount로 전달, TLS 검증 유지.

브라우저 재현은 backend.tests.gemini_fake_server:app + 명시적 YAKEUM_GEMINI_TEST_TRANSPORT=1,
합성 키/모델/임시 SQLite를 사용한다. 일반 LIVE_ENABLED=0, SYNTHETIC_ENABLED=1,
ADMIN_USERNAME=synthetic_admin, scenario approved-shape로 실행한다.
`YAKEUM_TEST_URL`은 loopback만 허용하며 실제 Render를 검사 스크립트 대상으로 사용하지 않는다.
