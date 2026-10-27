# Gemini 사진 경로 연결 준비 — 실제 호출은 미실시

2026-10-27. codex/mvp-completion, 시작 `71ed910a78fc6361c8881c8e24a79f2e61866fec`, clean.
전체 원격 fetch 후 새 팀원 변경 없음. 기존 코드/브랜치/DB를 되돌리지 않았다.

## 연결한 범위

개발용 로그인 화면 → 본인 가족 → 사진 추출 방식 선택 → 업로드 → 기존 SDK/provider/공통 adapter →
후보 수정·내용 확인 → B 정규화 검토 → D 비교 또는 보류 → 별도 복용 확인 → 정상 비교 저장/재조회/삭제.

기본값은 **Mock**. 기존 익명 사진 Mock/업로드/HIRA 경로에는 live 선택을 추가하지 않았다.
계정 화면에서 Gemini를 명시적으로 선택해야 별도 보호 endpoint로 요청한다.
키/모델/활성화가 없으면 503 안내이며 가짜 성공이나 Mock fallback을 반환하지 않는다.
프론트는 모드 변경/취소/파일 변경/가족 변경 시 후보·결과·복용 상태를 무효화한다.

Gemini가 제품을 읽는 것과 공식 제품 매칭은 다르다. **공식 매칭은 계속 LOCAL_MOCK**이다.
Mock 제품 목록에 없는 실제 제품은 UNMATCHED 등으로 비교 보류될 수 있다. 실제 식약처 연결 완료가 아니다.
사진 보류 결과는 현재 사진 정책대로 '확인한 결과' 저장 대상이 아니다. 원본/사유를 화면과 임시 초안에서
검토할 수 있지만 보류 사진을 별도 저장하는 정책 확장은 이번에 하지 않았다(HIRA 보류 저장과 다름).

## 계약/파일 영향

- 재사용: extraction_provider.extract_image_candidates → sdk.request_image → 기존 parser/adapter.
- 새 endpoint: POST /api/dev-account/families/{family}/photos/gemini-extract.
  입력 file/record_date/source_type, 기존 계정 세션·소유권·CSRF·Origin과 실제 이미지 검사를 그대로 적용.
- 공통 MedicationRecord/ExtractionResult/정규화/Reconciliation 상태·reason_code는 바꾸지 않는다.
- 계정 추출 응답 DEV_ACCOUNT_V1에 extraction_source(MOCK/GEMINI), official_data_mode=LOCAL_MOCK 추가.
  기존 소비자가 무시할 수 있는 출처 정보다. Gemini도 record.user_confirmed=false.
- documents.metadata에 내부 _extraction_source만 저장하고 처리 전 제거해 기존 Batch 모델로 전달한다.
  DB schema version 2 유지. 기존 문서는 MOCK으로 해석한다.
- Gemini가 포함된 계정 result에 extraction_sources={previous,current}를 저장해 재조회에도 출처를 표시한다.
  GEMINI는 **요청 경로의 출처**이며 실서비스 검증 완료라는 뜻이 아니다. 오프라인 검사는 같은 SDK에
  가짜 전송을 주입하므로 이 경우에도 경로 출처는 GEMINI다. 검증 기록과 함께 구분해야 한다.
- 기존 result.mode=LOCAL_MOCK는 순수 처리/공식 매칭 경로를 유지하며 출처는 extraction_sources로 구분한다.
- 정상/실패 혼합 후보는 기존 위치와 원본 순번을 보존한다. 실패가 남으면 전체 비교 보류.
  신뢰도 수치를 실제 정확도로 보거나 새 임계값으로 자동 확정하지 않는다.
- 정규화/비교/저장/조회에서는 다시 Gemini를 호출하지 않는다. 최초 업로드 후보 snapshot만 사용한다.
- 새 bridge만 서버 flag/설정/프로세스 호출 한도를 검사하고 threadpool에서 기존 함수를 실행한다.
  SDK는 timeout=60000ms, retry attempts=1(재시도 0), 요청 hook 1회 예산, max_output_tokens=4096.
- 호출 실패/시간 초과/잘못된 JSON은 기존 정제된 FAILED 결과. 키·원문 예외·사진·약 정보를 로그로 복사하지 않는다.

## 안전한 설정 — 지금은 활성화하지 않음

기존 개발 계정 설정 외에 다음 이름을 사용한다. 실제 값은 대화/Git/명령 이력에 남기지 않는다.

| 변수 | 의미 |
|---|---|
| GEMINI_API_KEY | Google AI Studio에서 만든 해당 개발 프로젝트 키. 클라우드 비밀 환경변수에 등록 |
| YAKEUM_GEMINI_MODEL | 계정에서 확인한 정확한 이미지 입력/JSON 응답 지원 모델 ID. 기본값/추측 모델 없음 |
| YAKEUM_GEMINI_LIVE_ENABLED | 별도 실제 호출 승인 후에만 1. 기본은 비활성 |
| YAKEUM_GEMINI_LIVE_MAX_REQUESTS | 기본 1, 허용 1~10. 단일 서버 프로세스의 누적 요청 시도 제한 |

키는 클라우드 설정의 secret binding 또는 로컬 터미널의 숨김 입력으로 전달한다.
`.env` 파일만 만든다고 backend가 자동으로 읽는 것은 아니다. 실제 실행 프로세스에 환경변수를 주입해야 한다.
로컬 Bash에서 키 입력 예시(여기서 실제 실행하지 않음):

```bash
read -r -s -p 'Gemini API key: ' GEMINI_API_KEY
export GEMINI_API_KEY
# 키 값을 echo/env/printenv로 확인하지 않는다.
```

새 키는 사용 범위/프로젝트와 예산 알림을 확인하고 브라우저 번들/VITE_* 변수에 넣지 않는다.
운영 보안이 갖춰진 환경이라는 뜻은 아니다. 이 단계의 개발 환경에는 합성 이미지만 사용한다.
시험용 가짜 키/모델은 자동 검사 프로세스에만 전달하며 실제 계정 키를 사용하지 않았다.

## 모델·현재 요금 확인 방법과 호출 계획

실제 계정/모델/요금제는 아직 결정하지 않았고 **현재 요금을 확인했다고 보고하지 않는다**.
다음 공식 화면에서 사용자가 확인한 뒤 정확한 모델 ID와 가격 기준일/통화/무료 또는 유료 tier를 정한다.

- 키/프로젝트: https://aistudio.google.com/apikey
- 모델과 입력 지원: https://ai.google.dev/gemini-api/docs/models
- 요금/무료 범위: https://ai.google.dev/gemini-api/docs/pricing
- 계정의 사용량·할당량·결제 설정도 확인. 무료 범위는 모델/계정/지역/요금제에 따라 다르다.

**제안한 최초 실호출 시험은 합성 PNG 800×500 한 장, 분석 1회, 모델 조회 0회, 자동 재시도 0회**다.
출력 상한은 4096 tokens. 이전/현재 두 장을 모두 Gemini로 연결하는 전체 실호출 검사는 별도 2회 예산이 필요하다.
첫 1회가 실패하면 추가 호출하지 않고 원인부터 검토한다. 오류/시간 초과도 서버 시도 한도를 사용한다.

현재 예상 금액은 모델/단가 미확정으로 **미산정**이며 무료나 고정 금액을 보장하지 않는다.
선택한 모델의 이미지 입력 토큰 I와 과금 출력(모델에 따라 thinking 포함) O를 확인한 뒤,
토큰 요금 모델이면 `호출 수 × (I × 입력 100만-token 단가 + O × 출력 100만-token 단가) / 1,000,000`으로 계산한다.
이미지 별도 과금/무료 할당량이 있으면 해당 표를 적용한다. 출력은 O<=4096 기준으로 검토하되
입력 이미지 토큰 수를 근거 없이 추정해 비용 상한으로 단정하지 않는다.
**모델·요금 기준과 예상 비용을 확인하고 1회 승인을 받은 뒤에만 활성화한다.** 이번 실제 호출 비용은 0이다.

프로세스 호출 한도는 금액 한도가 아니며 프로세스 재시작/여러 worker에서는 별개다.
시험은 단일 worker로 하고 재시작으로 예산을 반복 소비하지 않는다. 추가 시도는 별도 승인/설정 확인이 필요하다.

## 실호출 시 확인할 것과 중단

1. 가상 데이터·키 비밀 주입·정확한 모델 ID·승인된 1회 예산 확인. 자동 모델 목록 조회하지 않기.
2. 한 장만 업로드해 후보 수/누락/숫자·성분·함량·순번·user_confirmed=false 확인.
3. 모르는 값이 null/경고인지, 내용 확인 전 자동 확정되지 않는지 확인.
4. 실패/빈 응답/시간 초과/요금·설정 오류면 중단. 원문 오류/키/사진/약 내용을 로그나 채팅에 붙이지 않는다.
5. 서버를 중지하고 LIVE_ENABLED를 제거한 설정으로 재시작해 추가 웹 호출을 차단한다.
   실행 중인 프로세스의 환경변수는 다른 터미널 export만으로 바뀌지 않는다.
6. 이미 전송된 요청은 화면 취소로 중단/환불되지 않을 수 있다. 자동 재시도하지 않는다.
7. 계정 사용량 화면에서 실제 소비를 확인한다. 키 노출이 의심되면 프로젝트 설정에서 폐기/교체한다.

키/모델/1회 비용 결정과 승인이 남아 있다. 실제 인식 성능·실제 Gemini 응답·실제 MFDS·실제 건강정보,
운영 인증/암호화/백업/배포는 이번에 확인하지 않았다. 의료적 판단을 제공하는 서비스로 표현하지 않는다.

## 오프라인 검증 방식

backend/tests/test_gemini_account.py는 실제 고정 SDK에 HTTPX MockTransport만 주입한다.
정상/혼합 오류/읽기 불가·JSON/설정 누락/503/ReadTimeout/1회 시도·예산 차단·가족 권한·저장/삭제를 검사한다.
브라우저는 backend.tests.gemini_fake_server:app이라는 **명시적 테스트 서버**를 사용했다.
이 서버는 YAKEUM_GEMINI_TEST_TRANSPORT=1 없이는 실행되지 않으며 Google SDK Client의 HTTP 전송을
MockTransport로 교체해 모든 외부 네트워크를 차단한다. production app에 가짜 응답 선택 기능을 추가한 것이 아니다.
가상 모델/키만 사용하고 scenario 파일에는 normal/mixed/error/timeout/bad-json 이름만 저장한다.
SDK 가짜 요청 9회, 실제 Google 요청·모델 조회·MFDS 호출 0회로 구분한다.

클라우드 네트워크도 확인해야 한다. 현재 정책 목록에는 generativelanguage.googleapis.com이 없고,
런타임 정책 상태는 unknown이므로 실제 접속 가능하다고 가정하지 않는다.
승인된 실제 시험 전 클라우드 환경 설정에서 해당 SDK 목적지의 접근 허용과 적용 상태를 확인한다.
프록시 우회·TLS 검증 해제는 하지 않는다. 실호출 서버는 --reload 없이 단일 worker로 실행한다.

## 실행한 최종 검사

- 백엔드 전체 **344 passed**, 내부 subtest 5 passed(독립 개수에 합산하지 않음), 실패/xfail 0.
  기존 Starlette deprecation 경고 1개. 새 보호된 Gemini 경로 검사 12개 포함.
- 프론트 기존 7 script 그룹, strict TypeScript/Vite build 통과(48 modules).
- 오프라인 Gemini 브라우저 **13개 그룹** 통과: 실제 SDK 가짜 전송 → 후보 수정/확인 → B/D →
  별도 복용 → 저장·재로그인 → 출처 표시, 혼합 실패, 오류/시간초과/잘못된 JSON, 취소·가족 변경 늦은 응답.
- 기존 삭제 **13개**, 계정 사진 저장 **7개**, HIRA 저장 **10개**, 사진 업로드 **10개**,
  Mock/HIRA 통합 **13개 그룹** 통과. 그룹은 중복 범위가 있어 독립 테스트 총계로 합산하지 않는다.
- 360/390/768/1280px 가로 넘침 없음, browser runtime errors 0, 실제 외부 의료 API 요청 0.
- Gemini 가짜 HTTP 9회만 기록. 정규화/비교/저장 단계 추가 추출 없음.
- pip check / git diff --check 통과. 실제 키/사진/약 정보/개인정보/DB/검사 생성물은 Git에 넣지 않는다.
- 실제 Google 호출/모델 조회/현재 가격 조회/인식 정확도/운영 배포는 미실행으로 남긴다.

```bash
# 저장소 루트, 프로젝트 Python 환경
python -m pytest backend -q
python -m pip check
pnpm --dir frontend test
pnpm --dir frontend build
```

브라우저 오프라인 서버는 8044/Vite 4203, 일반 회귀 서버는 8045/Vite 4204에 격리 실행했다.
오프라인 서버만 테스트 flag·합성 모델/키·HTTPX 가짜 전송·/tmp 시나리오 파일을 사용했다.
일반 회귀 서버는 실제 Gemini 활성화 없이 기존 경로만 검사했다. 기존 실행/DB는 보존했다.

```bash
# 오프라인 harness가 켜진 환경에서만, 실제 키를 넣지 않는다.
YAKEUM_TEST_URL=http://127.0.0.1:4203/ \
YAKEUM_GEMINI_FAKE_SCENARIO=/tmp/yakeum-gemini-offline/scenario.txt \
YAKEUM_TEST_PYTHON=/tmp/yakeum-task-a-venv/bin/python \
YAKEUM_BROWSER_EXECUTABLE=/usr/bin/chromium \
YAKEUM_PLAYWRIGHT_MODULE=/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright \
node frontend/tests/account-gemini.browser.cjs
```
