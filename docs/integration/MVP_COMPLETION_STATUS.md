# 팀장 주도 MVP 개발 현황과 실행 순서

2026-10-27 한국 시간. 팀장 최슬기의 요청으로 A/B/C/D 남은 작업을 함께 진행한다.
이 문서는 과거 TASK D 한정 작업 범위와 구분되는 새 작업 기록이다.

## 기준과 원격 검토

시작 checkout: codex/task-d-weekly-integration,
a98a4a1f706e5e5c50fe1015650c6d715ff096aa, 작업 트리 clean.
`git fetch origin` 성공. 기존 통합본에서 `codex/mvp-completion`을 생성했다.
기존 원격·로컬 팀원 브랜치는 수정하지 않는다. 로컬 A d85e537도 참조 그대로 보존한다.
다른 사람 컴퓨터의 미푸시 변경은 확인할 수 없다.

| 원격 | 확인 SHA | 실제 포함 관계와 코드 검토 |
|---|---|---|
| D 통합 | a98a4a1f706e5e5c50fe1015650c6d715ff096aa | 시작 HEAD와 동일 |
| A | 2787918765e7e9724a1d2f1215b69e6296801a86 | tip 자체는 조상이 아니다. SDK/provider/의존성/SDK 검사/수동 사전검사 도구가 a98a4a1에 선별 반영되어 원격과 동일. legacy·미디어는 제외 |
| B | 0721848aab2c4e41765ebd8e529e02d20613fe55 | 조상(HEAD만 21커밋 추가). HIRA/MFDS/normalization은 보존, D structured 연결 추가 |
| C | d797bc89de5e0fad001d9d152a81f1ff8df9875e | tip은 조상 아님(HEAD 25, C 1). 실제 접근성 diff는 bd4af98에 선별 반영. D는 useId namespace·AbortController·혼합 실패 보존·외부 loadResults 연결을 추가로 유지 |
| D 원래 기능 | 1316f18057546737e1381ec2094999c752f06a19 | 조상. 비교·현재 복용상태 보존 |
| main / develop | c9d4f5b / 74e9783 | 조상. 변경하지 않음 |

기타 원격 codex/a-extraction-contract, b-d-c-integration, b-to-d-integration,
current-intake-ui, current-intake-ux-polish는 모두 시작 HEAD의 조상이다.
이번 fetch에서 새로 이동한 원격 tip은 없었다. 커밋 날짜나 브랜치 이름만으로 판단하지 않았다.
A/C 전체 병합은 구형 main.tsx·parser·취소 처리 등과 중복/회귀 위험이 있어 하지 않는다.

프로젝트 목적/기획 기준은 AGENTS.md, README, TEAM_START_GUIDE, TASKS와 각 Task 안내서다.
별도 기획서 파일은 현재 checkout에서 발견하지 못했다. DATA_SCHEMA/API_CONTRACT,
HIRA_COMPARISON_HOLD_V2, A_PUBLISHED_SDK_INTEGRATION, MVP_DEMO와 실제 코드를 대조했다.

## 현재 완성도 판단

과거 60%를 확정값으로 재사용하지 않는다. 아래 10개 영역을 같은 비중으로 두고
완성=1, 일부 구현=0.5, 미구현/실사용 미검증=0으로 평가하면 약 50%다.
이는 작업량/정확도/일정 확률이 아니라 **실사용 준비도에 대한 거친 추정**이다.
Mock 시연 경로가 동작하는 것과 실제 사용자 서비스 완성은 다르다.

| 영역 | 상태 | 근거/남은 일 |
|---|---|---|
| 사진 추출 | 일부(0.5) | SDK와 후보 복구 검사 있음. 화면은 가상 JSON, 실제 업로드부터의 경로/사진 성능 미검증 |
| HIRA·공식 매칭 | 일부(0.5) | XLSX parser·정규화·Mock 완주. 실제 HIRA export·공식 MFDS 필드 명세/함량 연결 미검증 |
| 비교·보류 | 구현(1) | v2 null/0건 구분, 반복/미확인 전체 보류. 대표 선택은 자동화하지 않음 |
| 화면·후보 확인 | 구현(1) | 원본/수정/정규화/복용확인/타임라인, 반응형과 접근성 회귀 |
| 취소·가족 전환 | 구현(1) | 이전 결과 제거와 늦은 응답 차단. 가족 선택은 실제 접근 권한이 아님 |
| 자동 회귀 기반 | 구현(1) | 가상 백엔드·프론트·브라우저 검사. 실제 서비스 검사와 구분 |
| 영구 저장 | 없음(0) | 화면 메모리, 새로고침하면 소멸 |
| 로그인·가족 권한 | 없음(0) | 현재 UUID는 보안 장치가 아님 |
| 배포·운영 | 없음(0) | 로컬 개발 실행만 확인 |
| 실제 사용자 검증 | 미검증(0) | 가상 시연 영상 있음. 사용자 사용성/실제 인식 평가 미실시 |

## 이번 변경: 실제 연동 전 오류·보안 기반

1. 제품 한 개의 숫자 오류가 정상 후보까지 지우는 오류를 먼저 재현했다(기존 4 pass + 1 xfail).
2. parser/models에 내부 실패 슬롯만 추가하고 adapter가 위치별 FAILED를 전달한다.
   정상/오류/정상에서 뒤 정상 source_record_id는 :3 그대로다.
   실패 후보 원문은 오류 문구/로그로 복사하지 않는다. 외부 결과 필드/상태/오류 코드는 그대로다.
3. ingredients=[{}], 전체 null, 부분 복합제의 미확인 성분에 기존 경고를 제공한다.
   확인된 성분과 원본 null은 보존하며 추정값을 넣지 않는다.
4. SDK 가짜 응답을 D 처리까지 연결해 정상 후보 보존 + 전체 비교 보류를 확인한다.
   실패가 남았는데 정상 후보만 비교해 신규/중단으로 판정하지 않는다.
5. MFDS 예외/응답 resultMsg에 키·요청 URL·건강정보가 포함되면 경고/로그로 유출되는
   문제를 합성 문자열로 재현했다(검사 2개 실패). 외부 문구를 고정 안전 문구로 바꾸고
   resultCode는 짧은 숫자만 노출한다. 정상 매칭/캐시/재시도 정책은 유지한다.

공통 API/MedicationRecord 변경 없음. 내부 모델만 확장했고 소비자 C/D는 기존
배열의 정상·FAILED를 그대로 처리한다. 기존 xfail을 삭제로 숨기지 않고 정상 회귀로 전환했다.
과거 A 통합 보고서는 당시 상태의 이력이며 이번 상태는 이 문서가 후속 기록이다.

## 다음 구현 순서와 선행 조건

| 우선순위 | 작업 | 완료 기준 / 선행 조건 |
|---|---|---|
| P0 | 사진 업로드·후보 보관·확인 후 정규화 연결 | SDK를 재호출해 사용자가 본 후보가 바뀌지 않도록 원본 snapshot과 확인 버전을 연결. Mock 기본, live 명시적 선택. 크기/파일 실제 형식/취소·TTL 검사 |
| P0 | 저장·인증·가족 접근의 최소 계약 | 서버에서 소유권 검사. 비밀번호 안전 해시·HttpOnly 세션·CSRF·로그아웃/만료. 가족 UUID만으로 타인 자료 조회 불가. 저장은 가입자별 opt-in; 원본 사진 기본 미보관 |
| P0 | DB repository와 마이그레이션 | MedicationRecord 의미 보존. 원본·수정·정규화·확인 구분, 트랜잭션/재업로드 멱등성/삭제·보관기간/백업 검토. 클라우드 임시 디스크를 운영 저장으로 설명하지 않음 |
| P1 | MFDS 명세 확인 | 보험코드와 ITEM_SEQ 구분, 공식 성분·함량의 필드/출처 확인. 현재 설정은 가정이므로 live 성공 주장 금지 |
| P1 | 일반 사용자용 업로드 화면 | 내부 Mock 검사 화면과 실제 업로드 분리, 다음 행동 안내, 모바일/키보드 검사 |
| P1 | 배포 준비 | 컨테이너·상태 확인·same-origin·HTTPS/비밀값 주입·테스트 CI. 공개 배포는 별도 승인 |
| P2 | 사용자 검사와 30~60초 시연 갱신 | 합성 자료로 처음 방문→등록→확인→비교→복용→재방문. 실제 사용자는 동의 후 별도 검증 |

새 업로드/저장/인증 응답 계약은 구현 전에 문서화·영향 설명한다. 기존 v1/v2는 유지한다.
지금은 자동 대표 선택/중복 삭제/낮은 신뢰도 임계값을 임의 확정하지 않는다.
신뢰도는 실제 정확도가 아니다. 모든 추출 후보에 사용자 확인이 필요하고 성공 상태도 확정 아님.

## 외부 호출·중요 결정

이번 Gemini 분석/모델조회/MFDS 호출 0회, 외부 서비스 비용 발생시키지 않음.
환경 상태 조회에서 설정된 비밀값 바인딩 없음. 키의 존재/승인을 가정하지 않는다.
실호출 전에 서비스·모델·가격 또는 계정 무료 범위·최대 호출수를 확인하고 별도 안내한다.
후보 제안: 합성 이미지 Gemini 1회(재시도 0), 공식 확인된 MFDS endpoint에 최소 조회.
아직 모델/계정 할당량을 모르므로 비용을 무료/고정값이라고 보장하지 않는다.

운영 준비 전에는 테스트 계정·가상 자료만 사용한다. 실제 건강정보는 업로드하지 않는다.
권한 없는 가족 접근 거부, 원본/로그 최소화, 비밀값 마스킹, 암호화 전송, 삭제/보관 동의,
백업 복구 및 공개 demo에 실제 자료가 섞이지 않는지 검증이 필요하다.

## 실제 실행한 검사

```bash
# 저장소 루트
/tmp/yakeum-task-a-venv/bin/python -m pytest backend -q
# frontend
pnpm test
pnpm build
YAKEUM_TEST_URL=http://127.0.0.1:4195/ \
YAKEUM_TEST_PYTHON=/tmp/yakeum-task-a-venv/bin/python \
YAKEUM_BROWSER_EXECUTABLE=/usr/bin/chromium \
YAKEUM_PLAYWRIGHT_MODULE=/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright \
node tests/photo-hira-integration.browser.cjs
```

- 최종 백엔드: **259 passed, 5 subtests passed**, xfail/실패 0。
  subtest는 독립 검사 수에 더하지 않는다. 기존 Starlette deprecation 경고 1개.
- 프론트: 기존 7개 script 그룹 통과, TypeScript strict/Vite 빌드 통과(43 modules).
- 브라우저: 최종 코드로 새로 띄운 backend 8010/Vite 4195에서 13개 그룹 통과.
  기존 8000/4192 프로세스와 구분했다. 임시 Vite config는 /tmp에 두고 기존 설정은 보존했다.
  360/390/768/1280px에서 가로 넘침 없음. runtime errors 0, externalApiRequests 0.
- 새 후보 복구가 SDK→D 보류까지 전달되는 경로는 HTTPX MockTransport로 별도 검사했다.
  브라우저는 기존 LOCAL_MOCK이며 실제 SDK/live 추출을 브라우저에서 실행한 검사는 아니다.
- git diff --check 통과. 변경 대상은 코드/테스트/Markdown뿐. 실제 사진·환자자료·키·env·생성물 없음.
- 아직 미실행: 실제 Gemini/MFDS·실제 사용자 HIRA·DB·권한·운영 배포·새 사용자 검사.

저장되는 첫 단계는 상태 조사·우선순위 정리·기존 추출 오류/로그 보안 수정이다.
실제 업로드·저장·인증까지 완료한 통합본으로 표현하지 않는다.
