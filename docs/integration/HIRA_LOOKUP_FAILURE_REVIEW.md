# HIRA 실매칭 조회 실패: 원인 미확인과 안전한 진단 보완

2026-10-30 (한국 시간), codex/mvp-completion, 시작 HEAD ca6b3ba.
이번 조사/구현에서 추가 Gemini/식약처 호출 0회. 설정 변경·배포·관리자 실행 기록 초기화 없음.

## 제공된 기존 증거

사용자가 제공한 `붙여넣은 텍스트.txt`는 화면의 'HIRA 원본·정규화·보류 사유' JSON이다.
SHA-256: c88dda03531a85604961fe3f184ed81aa140923bc143e3d8ccfb52521deb0d21.
원문/원본 행/문서 ID를 Git에 복사하지 않고 아래 안전한 사실만 기록한다.

- source_rows 2개(이전·현재)가 보존됐다.
- 양쪽 결과 UNMATCHED, match.source/id/method=null, record는 둘 다 존재한다.
- 동일한 제품명이며 준비한 공개 500mg 제품명과 일치한다. 원본 성분 함량 500mg/투약 단위 정, 보험코드 빈 값이다.
- '약품코드 없음'과 '식약처 조회에 실패했습니다. 원본을 보존하고 비교를 보류합니다.' 경고가 있다.
- comparison.executed=false, UNKNOWN_COMPARISON_FIELDS로 전체 비교를 보류했다.
- 첨부 JSON에는 processing/실제 조회 진단/HTTP 상태/실패 단계가 없다.

빈 보험코드는 합성 자료에서 의도한 값이다. 현재 로직은 원본 코드가 비어 있으면 그 일치를 요구하지 않으므로,
'약품코드 없음'이 외부 조회 실패의 원인이라는 근거는 없다.
제품/성분/함량의 단순 불일치·복수 후보·부분 페이지는 별도 보류 문구를 만든다.
이번 포괄적 '조회 실패'는 기존 코드의 transport/XML/응답 검증 예외 처리에서 발생했지만,
어느 분기인지는 과거 저장 정보만으로 복구할 수 없다.

## 관리자 조회와 실제 매칭 경로 대조

| 항목 | 관리자 단독 조회 | 사진/HIRA 실제 매칭 |
|---|---|---|
| 서버 key | MFDS_API_KEY | MFDS_API_KEY |
| host/경로 | apis.data.go.kr / 1471000/DrugPrdtPrmsnInfoService08/getDrugPrdtPrmsnDtlInq08 | 같은 fetch_xml 재사용, 동일 경로 |
| 인자 | serviceKey, pageNo=1, numOfRows=3, type=xml, item_name | 동일 5개 인자 |
| 검색어 | 타이레놀 | 원본의 정확한 전체 제품명. 이번 첨부는 준비한 500mg 전체 이름 |
| 인코딩 | Decoding 키를 urlencode로 한 번 | 동일. 이미 %XX로 인코딩된 키는 호출 전에 거절 |
| 시간/크기 | socket timeout=15초, 2MB | 동일 함수, 동일 제한. 전체 시간의 엄격한 15초 상한은 아님 |
| TLS/proxy | 기본 검증/기존 CA·proxy 사용, 리다이렉트 거절 | 동일 |
| XML | parse_sample_xml strict 파서, 자동 복구 없음 | 동일 |
| 페이지 성공 의미 | 유효한 첫 페이지 3건/전체 7건도 진단상 성공, all_candidates_received=false | 전체 후보 미수신이면 매칭/비교 보류 |
| 추가 확인 | 제품 ID·이름 등 필드/건수 | 단일 정확 제품·성분·500mg·정/보험코드(원본에 있을 때)도 확인 |
| 예산 | DB 영속 관리자 1회, 재시작/중복 요청 차단 | 처리 요청당 1회, 동일 원본 이름을 이전/현재에서 캐시 재사용 |

키 실제 값/Render 당시 설정은 조회하지 않았으며 동일 값이었다고 별도로 증명한 것은 아니다.
전체 검색어의 차이가 오류 원인인지, 일시적인 네트워크/서비스 문제인지 **미확인**이다.
관리자 실조회 성공이 모든 검색어/시각/응답에서 성공함을 보장하지 않는다.

## 기존 로그 조사 범위

현재 연결된 도구에는 Render 로그 조회 기능이 없다. Render 계정/서버의 실제 로그 원문을 읽지 않았다.
확인 가능한 기존 첨부·저장소 기록·기존 코드에는 이번 실패의 상세 오류 분류가 없다.
기존 LiveLookup은 예외를 ERROR 하나로 묶고 HTTPError stream을 읽지 않고 닫았다.
기존 B 정규화의 건수 로그는 외부 조회 전의 원본 정리 단계일 수 있어 원인 증거로 사용할 수 없다.
과거 cloud 503/envoy 기록이나 Render 관리자 성공을 이번 HIRA 응답의 HTTP 상태로 대입하지 않는다.
원문을 복구하기 위한 재호출은 하지 않았다.

## 보완한 진단 계약

공통 MedicationRecord/정규화 상태/reason_code·보류 정책·원본/권한은 유지한다.
MFDS_LIVE의 사진·HIRA 결과에만 선택적 `official_lookup`를 추가했다.
버전은 MFDS_LOOKUP_DIAGNOSTICS_V1이며 기존 결과에 필드가 없어도 읽을 수 있다.
기존 데이터의 원인·호출 횟수를 추정해서 backfill하지 않는다. DB 스키마 변경도 없다.

요약 필드:

- mode=MFDS_LIVE, provider=MFDS_DRUG, 키/쿼리 없는 고정 service_path.
- request_attempts, cache_reuses, budget_skips, 재시도/다음 페이지 0회, page=1/size=3/timeout=15.
- queries는 실제 시도 단위로만 기록. query_index만 사용하고 검색어/제품명/문서·사용자 ID를 넣지 않음.
- DNS_RESOLUTION / PROXY_CONNECTION / TLS_CERTIFICATE_VERIFICATION / TLS_NEGOTIATION /
  TIMEOUT_STAGE_UNDETERMINED / HTTP_FAILURE / XML_INVALID / API_RESULT_NOT_SUCCESS /
  PAGINATION_* / PRODUCT_FIELDS_INVALID / DUPLICATE_PRODUCT_IDS / PRODUCT_MAPPING_FAILED 등 고정 분류.
- HTTP 오류에는 관리자와 같은 safe_http_error를 재사용해 숫자 상태·허용 헤더·고정 본문 신호만 보존한다.
  응답을 같은 stream에서 제한 크기로 읽는 것으로 새 요청이 아니다.
- 정상 XML 이후의 부분 페이지에는 total_count/received_count와 INCOMPLETE_PAGE를 표시한다.
  조회 완료여도 제품·함량 매칭이 미확인일 수 있으므로 조회 성공과 비교 성공은 구분한다.

서버는 실패 시 `MFDS_MATCH_FAILURE category=... phase=... http_status=...`만 기록한다.
예외 원문/traceback/키/전체 URL/검색어/응답 본문/헤더 전체는 로그에 넣지 않는다.
HTTP500/503이나 envoy 신호만으로 원 서버/프록시 위치를 확정하지 않는다.
request_attempts는 시도 수이며 원 서버 도달/과금 성공을 확정하는 값이 아니다.
같은 오류를 이전/현재 양쪽에서 표시해도 캐시 재사용이면 로그/외부 요청은 1회다.

## 화면·저장

- 사진 처리 결과와 저장 사진, HIRA 처리 결과와 저장 HIRA에 같은 안전한 진단 영역을 추가했다.
- 상세 내보내기에도 mode 또는 processing과 official_lookup를 포함해 출처가 복사에서 빠지지 않게 했다.
- 신규 결과 저장/재조회 시 JSON과 함께 출처·진단을 보존한다. 현재 선택한 Mock 모드로 덮어쓰지 않는다.
- 과거 MFDS_LIVE 결과에 상세 진단이 없으면 '이전 버전 결과에는 상세 진단 정보가 없습니다.
  실패 원인은 미확인입니다. 진단을 얻기 위해 재조회하지 마세요.'로 안내한다.
- 단순 열기/상태 확인/저장/재조회는 식약처 요청을 만들지 않는다.
- 별도 실패 재시도·설정 활성화·과거 진단 slot 초기화 기능을 추가하지 않았다.

## 실제 실행한 오프라인 검사

- `python -m pytest -q backend`: 전체 실행 **537 passed**, PostgreSQL 39개는 이 실행에서 건너뛰고 별도 가상 DB로 검사. subtests 5 passed.
- 이후 비XML 진단 회귀를 추가한 최종 관련 실행:
  `python -m pytest -q backend/tests/test_mfds_lookup_diagnostics.py backend/tests/test_live_mfds_matching.py`: **43 passed**.
- loopback 가상 PostgreSQL에서 `python -m pytest -q backend/tests/test_postgres_integration.py`: **39 passed**.
- `pnpm test`: 프론트 테스트 스크립트 10개 통과. `pnpm build`: 타입 검사/Vite(53 modules) 통과.
- `node frontend/tests/live-mfds-matching.browser.cjs`: **6개 그룹 통과**.
  실제 앱/가상 계정으로 사진·HIRA 출처/안전한 진단/보류/저장·재조회,
  timeout 분류, Mock 전환 시 저장 출처 보존, 구형 진단 미포함 결과의 원인 미확인 표시를 확인했다.
  실제 외부 요청 0, runtimeErrors=0. 360/390/412/1280px 가로 넘침 없음.

Python은 /tmp/yakeum-mfdstest/bin/python이다. 각 실행에는 기존 Starlette/httpx deprecation warning 1건이 있었다.
검사 묶음은 겹치므로 합산해 독립 테스트 수로 표시하지 않는다.
모든 전송/HTTPError/응답은 가짜다. 새 진단 검사 13개는 DNS/프록시/TLS/시간 초과,
503/envoy/고정 upstream 신호, HTTP200 비XML, XML/API/페이지/제품 필드 오류,
부분 페이지와 예산·캐시 통계, 키/URL/검색어 비노출을 확인했다.
DB 구조/기존 자료/권한/비교 정책/관리자 1회 ledger는 변경하지 않았다.
실제 Render의 다음 오류를 관측한 것은 아니며, 상세 원인 확인을 위한 새 호출도 하지 않았다.
