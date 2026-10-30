# Render 성공 증거와 사진·HIRA 실제 매칭 경로 준비

2026-10-30 (한국 시간), codex/mvp-completion. 시작 HEAD d390914.
이번 추가 실제 Gemini/식약처 호출 0회. Render 설정 변경·배포·실행 기록 초기화 없음.

## 1. Render 실조회 성공 증거

[사용자가 제공한 관리자 결과](evidence/render-mfds-success-20261030.json)를 그대로 의미 보존해 기록했다.
이는 사용자가 Render에서 확인한 결과이며 이번 작업에서 에이전트가 다시 호출한 응답이 아니다.
started_at은 2026-10-29T23:47:56.163527Z, **한국 시간 2026-10-30 08:47:56**이다.
state=FINISHED, consumed=true, 요청 1회/재시도 0회, api_success=true, xml_valid=true.
정상 API 응답을 받은 범위의 인증·XML·제품 필드·페이지 검증 성공으로 기록한다.
배포 SHA/실제 환경변수 값은 이번에 조회하지 않았다.

전체 검색 7건 중 3건만 받았다. 단일 후보 증거=false, 사용자 자료 대비 성분·함량 검증=false다.
세 제품 모두 보험코드 미확인, 함량은 첫 제품 1개 미확인/둘째 1개 직접 매핑/셋째 4개 직접 매핑이다.
이는 공식 전체 명세 확정·전체 후보 조회·실제 매칭/비교 완료 증거가 아니다.
클라우드의 기존 503을 Render 장애라고 단정했던 기록은 없으며 두 환경의 결과를 구분한다.
관리자 고정 slot과 consumed 기록은 변경하지 않는다.

## 2. 추가한 명시적 경로

로그인한 사용자 소유 가족의 기존 처리 API에 선택적인 official_mode를 추가했다.
생략/기본값은 LOCAL_MOCK, 허용되는 다른 값은 MFDS_LIVE뿐이다.

- 사진: `/api/dev-account/families/{family}/photos/process` JSON의 official_mode.
- HIRA: `/api/dev-account/families/{family}/hira/process` multipart의 official_mode.
- 공개 local-demo/일반 HIRA v1/v2는 기존 Mock 그대로다. 자동 전환하지 않는다.
- 실제 경로는 서버 `YAKEUM_MFDS_MATCH_ENABLED=1`과 비공개 `MFDS_API_KEY`가 둘 다 필요하다.
  관리자 진단용 YAKEUM_MFDS_PROBE_ENABLED와 다른 설정이다.
- 키/활성화가 없으면 503으로 중단한다. 성공한 Mock 결과로 fallback하지 않는다.
- 이번에는 위 설정을 저장/적용하지 않았다. 기존 키가 있어도 새 flag가 없으면 실제 매칭은 꺼져 있다.
- 같은 계정의 기존 요청 함수와 서버 세션·Origin·CSRF·가족 소유권 검사를 재사용한다.
  처리 전에 권한을 검사하고, 저장/조회/삭제에도 기존 소유권 검사를 유지한다.

사용자 화면에는 가족 작업의 **실제 식약처 매칭 요청 (별도 승인·서버 활성화 필요)** 선택을 추가했다.
선택/해제하면 가족 작업 화면을 새로 구성해 이전 결과·진행 요청을 취소한다.
사진 후보 확인과 실제 복용 확인은 기존처럼 별도다.
UI/저장 재조회는 선택값이 아니라 저장된 mode/processing.official_data_mode로 출처를 표시한다.
MFDS_LIVE는 **실제 요청 경로** 표시이지 모든 제품이 확인됐다는 뜻이 아니다.

## 3. 조회 제한과 보류

의약품 단일 08 상세 API의 기존 fetch_xml을 재사용한다.
제품명 원문으로 pageNo=1, numOfRows=3, type=xml 조회하며 보험코드 검색이나 건강기능식품 조회는 하지 않는다.
자동 리다이렉트·재시도·다음 페이지 조회는 없다.

**MVP 제한: 처리 요청 1개당 최대 1회**이며 이전·현재 동일 제품명은 그 요청 내에서 캐시를 재사용한다.
다른 제품이 더 있으면 한도 보류다. 다제품 전체 조회/자동 페이지 수집은 구현하지 않았다.
사진의 정규화 미리보기와 최종 확인은 별도 처리 요청이므로, 명시적으로 누를 때 각각 최대 1회가 될 수 있다.
서버 재시작/다른 처리 요청까지 포괄하는 총 호출 예산이나 캐시는 이번 일반 매칭 경로에 없다.
**관리자 진단의 영속 1회 slot을 재사용/초기화하지 않는다.**
요청 불명확 시 자동 재처리하지 않는다. 실제 경로의 외부 실행/예산 승인은 별도로 필요하다.

다음은 원본과 정규화 결과를 유지하고 비교를 보류한다.

- totalCount가 받은 전체 후보 수보다 큼: 부분 응답. 그중 하나를 골라 단일 후보라고 하지 않음.
- 0건, 복수 후보, 중복 ID, 잘못된 XML/성공 코드/페이지 메타데이터, 네트워크/HTTP 오류.
- 제품명이 원문과 정확히 대응하지 않음. 제품명에서 함량을 제거하거나 유사도만으로 확정하지 않음.
- 원본 보험코드가 있는데 공식 EDI_CODE와 일치를 확인하지 못함. 빈 EDI_CODE를 추정하지 않음.
- 원본/공식 성분 집합·분량·단위가 누락·중복·불일치. 원본 성분·함량을 공식 값으로 덮어쓰지 않음.
- 현재 공식 함량 파서는 1정 기준의 직접 분량만 지원한다. 과립/‘~으로서’ 환산/다른 기준량은 보류.
- 원본 투약 단위도 정이어야 이 기준과 대응시킨다. 1회 투약량·일일 횟수와 제품 함량은 구분한다.
- mg/밀리그램은 같은 단위 표기만 대응하며 g↔mg 같은 배율 환산은 하지 않는다.

정확한 단일 제품·성분·함량 대응이 모두 확인됐을 때만 MATCHED와 공식 ID를 설정한다.
기록 내용의 사용자 확인/복용 여부를 자동 확인하지 않는다. 실패/PARTIAL/UNMATCHED는 live 비교를 보류한다.
HIRA의 함량 열이 없는 실제 자료는 원본 함량 미확인으로 보류될 수 있다. 임의로 보완하지 않는다.
공식 함량 파서의 제한·정확한 제품명 조건 때문에 정상 약품도 현재 지원 범위 밖이면 보류될 수 있다.

## 4. 계약·저장 영향

공통 MedicationRecord, Reconciliation 상태/reason_code, 복용 상태 의미는 유지한다.
기존 요청·공개 API·기존 저장 JSON은 바꾸지 않는다. 신규 DB 테이블/마이그레이션도 없다.
모드를 생략한 구형 사진 요청의 reviews 저장 모양도 유지한다.

- 사진 결과 mode는 명시적 실제 요청에서만 MFDS_LIVE. 기존 LOCAL_MOCK 유지.
- 실제 HIRA 결과는 **TASK_D_HIRA_MFDS_V1**으로 구분하며 기존 v2 구조와 보류/null 구분을 재사용한다.
  processing.official_data_mode=MFDS_LIVE. 공개 TASK_D_HIRA_V2는 그대로 LOCAL_MOCK다.
- 계정 저장 envelope와 기존 테이블을 재사용한다. 결과 JSON에 출처/버전을 보존한다.
- 프론트는 실제 모드를 명시적으로 요청했을 때만 해당 버전을 받아들인다.
  저장 자료는 저장된 출처/버전을 검사하며 알 수 없는 모드는 거절한다.
- HIRA 보류를 저장 후 다시 열어도 comparison.executed=false, reconciliation_result=null, 보류 이유·원본 참조가 유지된다.
  정상 비교 0건과 구분한다. 사진 보류의 명시적 저장 제한은 기존 정책 그대로다(처리 초안은 기존 DB 경로에 보존).
- 매칭 모드를 바꾸거나 가족/사용자를 바꾸면 이전 화면/늦은 응답을 버린다.

## 5. 검증과 남은 단계

검사는 가상 사용자·가상 이미지·XLSX·XML·전송만 사용한다. 실제 건강정보나 실제 키를 fixture로 쓰지 않았다.
오프라인 검증 성공은 Render에서의 새 매칭 경로 실동작 확인을 뜻하지 않는다.
이번 Render 성공 증거는 관리자 단독 조회이며 새 사진·HIRA 연결의 실조회 증거와 구분한다.

다음 실제 검증은 사용자가 배포·YAKEUM_MFDS_MATCH_ENABLED·호출 예산을 별도 승인한 뒤 진행한다.
현 단계에서 새 flag를 켜거나 배포하거나 관리자 기록을 지우지 않는다.

### 실제 실행한 검사 결과

- `python -m pytest -q backend`: **525 passed**, subtests 5 passed. 기본 실행에서 PG 검사는 제외하고 아래 별도 환경에서 확인했다.
- loopback 전용 가상 PostgreSQL에서 `python -m pytest -q backend/tests/test_postgres_integration.py`: **39 passed**.
  기존 저장/권한/삭제/관리자 1회 검증과 실제 경로의 사진/HIRA 출처 저장을 포함한다.
- 비동기 HIRA의 외부 I/O를 threadpool로 분리한 뒤 관련 검사 43개 통과.
- 최종 오류 상태 분류 확인을 포함한 `python -m pytest -q backend/tests/test_live_mfds_matching.py`: **30 passed**.
- `pnpm test`: 테스트 스크립트 10개 통과. Mock/live 버전 혼동·fallback 응답 거절 검사를 추가했다.
- `pnpm build`: 타입 검사·Vite 빌드 통과(52 modules).
- `node frontend/tests/live-mfds-matching.browser.cjs`: **5개 그룹 통과**, 실제 외부 호출 0, runtimeErrors=0.
  사진 Mock 추출→실제 매칭 경로(가짜 XML)→비교→저장, HIRA 부분 응답→보류→저장/재조회,
  조회 오류의 보류, Mock 전환 시 이전 결과 제거, 선택 모드와 독립적인 저장 출처 표시를 확인했다.
- 기존 `node frontend/tests/account-storage.browser.cjs`: **7개 그룹 통과**, externalApiRequests=0.
  사진 저장·독립 복용 확인·재로그인·가족 변경·다른 사용자 차단·늦은 응답 차단 회귀를 확인했다.
- 360/390/412/1280px에서 가로 넘침 없음.

Python은 /tmp/yakeum-mfdstest/bin/python을 사용했다. 각 Python 검사에는 기존 Starlette/httpx deprecation warning 1건이 있었다.
검사 묶음은 중복되므로 합산해 독립 테스트 수라고 표현하지 않는다.
초기 새 HIRA fixture의 함량 열 위치와 구형 리뷰 JSON에 새 기본 필드가 추가되던 호환성 오류를 수정한 뒤 통과했다.
기존 검사의 성공 조건을 낮추거나 문제 검사를 삭제하지 않았다.
브라우저의 새 모드 전환 후 저장 재조회는 기존 목록 새로고침 동작을 사용했다.
실제 Render·MFDS의 새 사진/HIRA 경로, 다제품/전체 페이지 수집은 미검증·미구현 범위로 남는다.

후속 HIRA 조회 실패의 안전한 진단·출처 저장/표시는
[HIRA_LOOKUP_FAILURE_REVIEW.md](HIRA_LOOKUP_FAILURE_REVIEW.md)를 따른다.
이전 결과의 상세 정보가 없으면 원인 미확인으로 유지하며 확인을 위한 재호출은 하지 않는다.
