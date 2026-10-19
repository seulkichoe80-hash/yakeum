# B 실제 데이터 검증 계획 (HIRA Excel · 식약처 API)

상태: **미검증.** 아래 항목을 확인하기 전까지 코드의 컬럼명·URL·필드명·코드 체계는 가정이다.
원칙: 실제 환자 정보·심평원 원본 파일은 GitHub/AI 대화에 올리지 않는다. 비식별(또는 가상) 자료로만 확인하고, API 키는 환경변수 `MFDS_API_KEY`로만 쓰며 로그·커밋에 남기지 않는다.

## 1. HIRA 「내가 먹는 약! 한눈에」 파일 체크리스트
본인(또는 동의받은 사람)의 파일을 **로컬에서만** 열어 확인한다. 이름·주민번호·기관명 등은 지운 사본으로 기록한다.

| # | 확인 항목 | 확인 방법 | 코드 위치 |
| --- | --- | --- | --- |
| 1 | 시트 수와 시트 이름, 안내문/제목 행 수 | 파일을 열어 헤더가 몇 번째 행에 있는지 확인 | `parser.py` 헤더 탐지(상위 30행) |
| 2 | 실제 헤더 문자열 12개 (번호, 조제일자, 처방기관, 조제기관, 제품명, 약효분류, 성분명, 약품코드, 단위, 1회 투약량, 1일 투여횟수, 총 투약일수) 와 일치 여부 | 헤더를 그대로 복사해 `column_mapping.yaml` 별칭과 대조 (줄바꿈·공백 포함) | `column_mapping.yaml` |
| 3 | **처방기관 ≠ 조제기관** 인지, 병원/약국 중 어느 쪽이 어느 컬럼인지 | 처방전을 받은 병원과 조제받은 약국을 아는 행 1~2건으로 대조 | `prescribing_institution`, `dispensing_institution` |
| 4 | 날짜 의미: `조제일자`가 조제일인지, 셀 형식(날짜형/문자열/`YYYY.MM.DD`) | 셀 서식 확인, 처방일과 다른 날짜가 따로 있는지 확인 | `parse_date`, `dispensing_date` |
| 5 | `약품코드`의 의미와 자릿수 (보험 EDI 코드인지, 9자리 문자열인지, 앞자리 0 보존 여부) | 셀 서식이 텍스트인지 확인, 코드 몇 개를 건강보험 약가 목록에서 대조 | `drug_code`(String 보존) |
| 6 | `성분명`이 한 셀에 여러 개일 때 구분자(`/`, `,`, `+`), 함량 컬럼 유무 | 복합제 행 확인. 함량 컬럼이 없으면 `product_strength`는 공식 데이터로만 보완 | `_ingredients` |
| 7 | `단위`가 1회 투약량의 단위인지(정/캡슐/mL), `1회 투약량`의 소수·분수 표기 | 0.5, "1/2" 등 표기 샘플 수집 | `_num`, `unit` |
| 8 | 합계/소계/빈 행, 병합 셀, 하단 안내문 | 파일 하단·중간 확인 | 파서의 빈 행·병합 셀 처리 |
| 9 | 안전성 서한, 항혈전제 여부 컬럼 (현재 미사용) | 필요 시 `Evidence` 구조 결정 후 별도 반영 (공통 Schema 변경 사항) | — |

결과는 "확인함/다름(실제 헤더)/모름" 로 표에 남기고, 다르면 `column_mapping.yaml` 별칭만 수정한다. 가상 헤더 샘플을 `make_fixtures.py`에 추가해 회귀 테스트로 고정한다(실제 데이터 금지).

## 2. 식약처 공식 API 확인 계획
| # | 확인 항목 | 확인 방법 |
| --- | --- | --- |
| 1 | 사용할 API의 공식 명세(공공데이터포털): 의약품 제품 허가정보, 건강기능식품 품목제조신고 — endpoint URL, 요청 파라미터명, 응답 필드명 | 공공데이터포털 해당 API 상세 페이지의 명세서 확인. `mfds/api_config.yaml`과 1:1 대조 |
| 2 | 식별자 체계: `ITEM_SEQ`(품목기준코드)와 HIRA `약품코드`(보험코드)는 **같은 체계가 아님**. 응답에 보험코드(EDI) 필드가 있는지, 있다면 필드명과 파라미터 | 응답 샘플에서 코드 필드 목록 확인. 있을 때만 `insurance_code_param`, `fields.insurance_code` 설정 |
| 3 | 성분 필드: `MAIN_ITEM_INGR` 의 구분자·`[코드]` 접두 형식, 함량이 응답에 있는지(별도 성분 API 필요 여부) | 복합제 1건으로 응답 확인. 함량이 없으면 `product_strength`는 null 유지 |
| 4 | 건강기능식품 제품 ID(`PRDLST_REPORT_NO`)와 성분(기능성 원료) 필드 | 응답 확인 후 `ingredients` 채우는 방식 팀과 협의 |
| 5 | 호출 한도·응답 코드(`resultCode` 정상/데이터 없음), 페이징(`numOfRows`) | 명세서 확인 + 가상 질의 1~2회 |
| 6 | 이름 검색이 부분 일치인지, 정규화한 이름으로 후보가 충분히 나오는지 | 알려진 제품명 몇 개로 후보 수 확인 (개인 복용 정보 대신 일반 제품명 사용) |

실행 방법(키 발급 후): `export MFDS_API_KEY=...` → `python -m backend.services.normalization.cli 가상샘플.xlsx --real -v`.
키가 없거나 호출하지 못했으면 **"미검증"으로 기록**하고 결과를 성공으로 보고하지 않는다.

## 3. 검증 후 반영 순서
1. 헤더·API 명세 확인 결과를 표로 정리해 팀장에게 공유
2. `column_mapping.yaml`, `api_config.yaml`만 수정 (코드 변경 최소화)
3. 가상 픽스처와 테스트 갱신 → `python -m pytest backend/services -q`
4. 공통 Schema/Contract 변경이 필요한 사항(Evidence, 안전정보, 건강기능식품 ID, 새 오류 코드)은 코드로 우회하지 않고 팀장에게 먼저 보고

## 4. B→D 연동 협의 결정 반영 현황 (PoC 방향, 공통 Schema/Contract 변경 아님)
| # | 결정 | B 쪽 상태 | 근거 테스트 |
| --- | --- | --- | --- |
| 1 | 기준일 방식 우선: 원본 조제일 모두 보존. 이전/현재 선택은 D 책임 | 반영됨 (선택 기능 미구현) | `test_every_dispensing_date_is_preserved_and_nothing_is_collapsed` |
| 2 | 같은 약 반복행 자동 삭제·최신 1건 축약 금지 | 반영됨. 중복 경고만 남김 | `test_identical_repeated_rows_are_kept_with_duplicate_warning` |
| 3 | NormalizationResult status/match/warnings/errors 보존 | 반영됨 | `test_status_match_warnings_errors_are_carried_over` |
| 4 | HIRA `user_confirmed=false` 유지 (복용 여부 아님) | 반영됨 | `test_user_confirmed_false_and_confidence_null_for_all_hira_records` |
| 5 | 원본/공식명/규칙 정규화명 혼동 금지 | 원본 보존 반영. 단, 공통 Schema에 공식명 전용 필드가 없어 `product_name_normalized`에 공식명(단일 매칭) 또는 규칙값이 들어감 → **D 비교 영향은 팀 협의 대상** | `test_raw_product_name_is_never_overwritten` |
| 6 | 함량 null 은 null 유지 | 반영됨 (HIRA 성분이 있으면 공식 함량으로 덮어쓰지 않음) | `test_product_strength_stays_null_when_unknown` |
| 7 | 빈 성분 원본 보존, 성분만으로 매칭 확정 금지 | 반영됨 | `test_empty_ingredients_are_preserved_as_empty_list`, `test_ingredient_name_alone_never_confirms_a_match` |
| 8 | B→D 연결 코드는 D/API 통합 담당 | B 는 연결 코드 미작성 | — |
| 9 | ID PoC 잠정 규칙(UUID5/해시) 유지, 재업로드·중복·순서 회귀검증 | 반영됨 | `test_reupload_*`, `test_row_order_*`, `test_same_product_different_*`, `test_ids_do_not_depend_on_matching_outcome` 외 |

## 5. 현재 미검증 항목과 다음 확인 방법
| 항목 | 상태 | 다음 확인 방법 |
| --- | --- | --- |
| 실제 HIRA 파일 헤더·처방기관/조제기관·날짜·약품코드 의미 | 미검증 (가상 헤더만 사용) | 1장 체크리스트를 비식별 사본으로 수행 |
| 식약처 API URL·파라미터·응답 필드·성분 필드 | 미검증 (Mock/가짜 응답만 사용) | 2장 절차, 실제 키는 환경변수로만 사용 |
| HIRA 약품코드 ↔ 식약처 제품 식별자 체계 | 미확인. 보험코드 매칭(`insurance_code_param`)은 꺼져 있음 | 공식 명세 확인 후 `api_config.yaml`만 수정 |
| HIRA 성분 함량 컬럼 유무 | 미확인 (TASK 문서에는 함량 컬럼이 없음) | 실제 파일 확인. 없으면 `product_strength` 는 null 유지 |
| `product_name_normalized` 의미 통일 | 팀 협의 필요 (공통 Schema 사항) | 팀장·D 와 협의 후 결정 |
| D 연동 동작 | 미실행 (연결 코드는 D/API 통합 담당) | D 가 B 출력(`d_examples` 형태)으로 확인 |

## 6. 확인한 사실 / 가정 / 미검증 (2026-10-14 기준)
외부 API 호출은 하지 않았다(별도 승인 전 금지). 실제 건강정보·API Key는 사용하지 않았다.

| 구분 | 항목 | 근거 |
| --- | --- | --- |
| **확인한 사실** | HIRA Excel은 AI 없이 규칙 기반(openpyxl)으로 읽는다 | 코드·테스트(`test_hira_parser.py`) |
| **확인한 사실** | 원본 조제일·반복 조제행·status/match/warnings/errors를 보존한다 | `test_team_decisions.py` |
| **확인한 사실** | 공통 규격 변환 결과가 DATA_SCHEMA/API_CONTRACT 형태 점검을 통과한다 | `validate_common_result`, `test_adapter.py` |
| **확인한 사실** | B 출력을 D 통합 코드(`codex/b-to-d-integration`, 읽기 전용 실행)에 넣으면 용량 변경·미확인·신규가 예상대로 판정된다 | 7절 실험 A |
| **가정** | HIRA 헤더: 번호, 조제일자, 처방기관, 조제기관, 제품명, 약효분류, 성분명, 약품코드, 단위, 1회 투약량, 1일 투여횟수, 총 투약일수 | TASK_B 안내서의 필드 목록. 실제 파일 미확인 |
| **가정** | 식약처 의약품 API의 `ITEM_SEQ`/`ITEM_NAME`/`MAIN_ITEM_INGR`, 건강기능식품 `PRDLST_REPORT_NO`/`PRDUCT` | 공공데이터포털 명세 기억 기반. 실제 응답 미확인 |
| **가정** | `MAIN_ITEM_INGR`의 `[코드]이름\|…` 형식, 응답에 함량 없음 | 가짜 응답으로만 테스트 |
| **미검증** | 실제 HIRA 파일의 헤더·처방/조제기관 의미·날짜·약품코드 의미 | 1장 체크리스트 |
| **미검증** | 식약처 API URL·파라미터·응답 필드·코드 체계, HIRA 약품코드(보험코드)와 `ITEM_SEQ`의 관계 | 2장 절차. 보험코드 매칭은 기본 꺼짐 |
| **미검증** | 대용량 파일, 실제 사용자 흐름(업로드→확인→조회) | 이번 범위 아님 |

## 7. D 통합 실험에서 발견한 보완사항 (공통 계약 변경 없이 B 쪽에서 가능한 범위만 개선)
방법: `origin/codex/b-to-d-integration`을 임시 폴더에 풀어 B 현재 코드와 함께 읽기 전용으로 실행했다(저장소 파일은 변경하지 않음). 가상 Excel 입력만 사용.

| # | 발견 | 영향 | B 쪽 조치 | 남은 결정 |
| --- | --- | --- | --- | --- |
| 1 | **반복 조제**: 한 시점에 같은 약이 2줄 이상이면 D가 동률 후보로 보고 매칭하지 않아, 이어지는 약이 `NEEDS_CONFIRMATION` + `NEW`로 갈라짐(실험 B·C) | 계속 복용 중인 약이 "사라짐+신규"로 보일 수 있음 | 삭제·축약은 하지 않음(팀장 결정). 읽기 전용 진단 `repeat_report.find_repeat_groups` 추가: 반복 그룹과 조제일 목록 제공 | 대표 기록 선택/그룹 비교는 D·통합 계층 결정 |
| 2 | **UNMATCHED + 성분 없음**: 약품코드만 같으면 `MAINTAINED`(`SAME_INGREDIENT_SAME_STRENGTH`)로 판정됨(실험 A) | 성분·함량을 모르는데 "동일 성분·동일 함량"이라는 reason_code가 붙음 | B는 경고(`성분 정보 없음`)를 보존. 계약 변경 없이는 불가 | reason_code 의미 또는 별도 표시 방식(공통 계약) |
| 3 | **함량 null**: HIRA에 함량 컬럼이 없어 `product_strength`가 null → 함량 변화는 비교 불가 | `DOSE_CHANGED`는 투약량·횟수·단위 변화만 잡힘 | null 유지(추측 금지). 공식 데이터에 함량이 있어도 HIRA 성분을 덮어쓰지 않음 | 함량 보완 정책(식약처 함량 필드 확인 후) |
| 4 | **ID**: 재업로드·행 순서·날짜 서식이 달라도 `record_id`/`source_record_id` 동일, 반복행은 `-2`… 구분 | 문제 없음 | 회귀 테스트 유지 | PoC 잠정 규칙 최종 확정 |
| 5 | **제품명 정규화 일관성**: 단일 매칭이면 공식명, 미매칭이면 규칙 정규화명이 `product_name_normalized`에 들어감 | 시점마다 매칭 결과가 달라지면 이름 기반(3순위) 비교가 어긋날 수 있음. 코드·mfds ID가 있으면 영향 없음 | 변경하지 않음(공통 Schema에 공식명 필드 없음) | 통일 규칙(공통 Schema 협의) |

## 8. 실제 HIRA/MFDS 검증에서 막힌 사항과 필요한 입력 (2026-10-18)
코드 수정 없이 정리만 했다. 외부 API 호출과 실제 환자 파일 사용은 하지 않았다. **아래 항목은 모두 미검증이다.**

| # | 막힌 사항 | 막힌 이유 | 필요한 입력 (누가/무엇을) | 확인 후 바뀌는 곳 |
| --- | --- | --- | --- | --- |
| 1 | 실제 HIRA Excel 헤더 12개와 일치 여부 | 실제 파일 없음(가상 헤더만 사용) | **헤더 행만 남긴 비식별 사본** 또는 헤더 문자열 목록(데이터 행 없음) | `hira/column_mapping.yaml` 별칭 |
| 2 | 처방기관 ≠ 조제기관 컬럼 구분 | 같은 이유 | 위 헤더 + 병원/약국 구분을 알려 주는 가상 예시 1행(실제 기관명 제외) | `prescribing_institution`/`dispensing_institution` 매핑 |
| 3 | `조제일자` 의미와 셀 서식, `약품코드` 의미·자릿수 | 같은 이유 | 서식(날짜형/텍스트) 확인 결과, 코드 자릿수 | `parse_date`, `drug_code` |
| 4 | HIRA 성분 함량 컬럼 유무 | 같은 이유 | 헤더 목록 | `product_strength` 보완 정책 |
| 5 | 식약처 API URL·파라미터·응답 필드 | 공식 명세 미확인, **API Key·호출 승인 없음** | 공식 명세서(공공데이터포털) + 키 발급·호출 승인(팀장) | `mfds/api_config.yaml` |
| 6 | HIRA 약품코드(보험코드) ↔ `ITEM_SEQ` 관계 | 응답에 보험코드 필드가 있는지 모름 | 응답 샘플 1건 (환자 정보 없는 일반 제품) | `insurance_code_param`(현재 꺼짐) |
| 7 | 성분(`MAIN_ITEM_INGR`)·함량 응답 형식 | 위와 동일 | 복합제 응답 샘플 1건 | `parse_item` |
| 8 | 건강기능식품 제품·원료 ID 체계 | 공통 Schema TODO | 팀장 결정 + 응답 샘플 | `ingredients` 채우기 |
| 9 | A 코드와의 실제 연결(A→B) | A 코드 미병합, 통합은 팀장 몫 | 팀장 결정(`DESIGN_A_TO_B.md` 7장) | 진입점 구현 위치 |

실제 환자 파일은 GitHub와 AI 대화에 올리지 않는다. 확인은 로컬에서 하고 결과(헤더 문자열, 서식)만 문서화한다.

## 9. 이번 주 작업 결과 (설계·검증, 2026-10-18)
| 산출물 | 위치 |
| --- | --- |
| A→B 필드 매핑·상태 전달·`user_confirmed` 경계·진입점 시그니처 설계 | `DESIGN_A_TO_B.md` |
| Mock 기반 시나리오 15개(테스트 17건), 실행 PASS | `tests/test_structured_input_design.py` |
| D 전달용 결함 재현 사례 R1~R4 (D 브랜치에서 읽기 전용 실행 결과 포함) | `d_repro/README.md`, `d_repro/cases.json` |
| 기존 HIRA/MFDS/Adapter 회귀 | 기존 테스트 전체 통과 (아래 테스트 요약) |

테스트: `python -m pytest backend/services -q` → 112 passed (기존 91 + 설계 검증 17 + 재현 사례 점검 4). 실패 0, 실패 원인 기록 없음.
