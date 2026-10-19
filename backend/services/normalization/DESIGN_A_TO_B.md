# A → B 구조화 MedicationRecord 정규화 입력 경계 설계 (B팀)

> **상태: 설계 문서 + 가상 데이터 검증.** 구현 완료·통합 완료가 아니다.
> 공통 계약(`DATA_SCHEMA.md`, `API_CONTRACT.md`), A/C/D 코드, 팀장 통합본(`codex/*`)은 변경·병합하지 않았다.
> 검증용 프로토타입은 `tests/test_structured_input_design.py` 안에만 있으며 B 모듈로 승격하지 않았다(팀장 통합 코드와 중복 방지).

## 1. 기준과 범위
- A 쪽 기준: `origin/codex/a-extraction-contract` (SHA `4758dea`)의 `backend/services/extraction/adapter.py`, `models.py`, `backend/tests/test_extraction_contract.py`를 **읽기 전용**으로 확인했다. 내 브랜치에 병합하지 않았다.
- B 쪽 기준: `feature/data-backend` (기존 HIRA 파서·식약처 매칭·공통 Adapter 보존).
- 목표: AI가 만든 MedicationRecord **후보**를 HIRA 전용 파서에 억지로 넣지 않고, 별도 정규화 진입점으로 받는 경계를 정한다.
- 실제 HIRA 헤더·식약처 API 응답 스키마는 **미검증**이다. 모든 테스트는 MockMfdsClient와 가상 데이터만 사용했다. Mock 결과를 "공식 조회 성공"으로 보고하지 않는다.

## 2. 두 상태 체계는 다르다 (혼동 금지)
| | A `ExtractionResult.status` | B `NormalizationResult.status` |
| --- | --- | --- |
| 값 | `SUCCESS`, `NEEDS_CONFIRMATION`, `FAILED` | `MATCHED`, `PARTIAL`, `UNMATCHED`, `FAILED` |
| 의미 | AI가 후보를 얼마나 추출했는지, 사용자 확인 필요 여부 | 공식 데이터와 얼마나 매칭됐는지 |
| 확정 의미 | 둘 다 사용자 확정이 아님 (`user_confirmed=false`) | 매칭 결과일 뿐 복용 확정이 아님 |
| `FAILED` | 추출 불가, `record: null` | 파싱/정규화 불가, `record: null` |

두 체계를 **합치거나 서로 변환하지 않는다.** A 상태는 입력 정보로만 읽고, B 상태는 매칭 결과로만 정한다.

### 상태 전달 규칙 (제안)
| A 입력 | B 처리 | B 출력 상태 |
| --- | --- | --- |
| `FAILED` (`record: null`) | 조회하지 않음. A `errors`를 그대로 전달 | `FAILED`, `record: null` |
| `NEEDS_CONFIRMATION`, `record: null` (예: 제품명 없음, 자료 유형 불명) | 정규화할 대상이 없음. A `warnings`를 `errors`로 옮겨 사유 보존 | `FAILED`, `record: null` |
| `SUCCESS`/`NEEDS_CONFIRMATION`, `record` 있음 | 이름 매칭 수행 | `MATCHED`/`PARTIAL`/`UNMATCHED` |
| record의 `family_member_id`가 요청과 다름 | 조회하지 않음 | `FAILED` (`REQUIRED_FIELD_MISSING`, field=`family_member_id`) |
| record의 `product_name_raw`가 비었음 | 조회하지 않음 | `FAILED` (field=`product_name_raw`) |
| 조회 중 예외 | 예외 원문은 노출하지 않고 경고만 남김 | `UNMATCHED` + 경고, record 보존 |

- `warnings`: A 경고(ErrorDetail)를 **그대로 앞에 두고** B 경고를 뒤에 붙인다. 경고를 지우지 않는다.
- 계약 B에는 A의 `SUCCESS`/`NEEDS_CONFIRMATION`을 담을 필드가 없다. 현재 설계에서는 사라진다(결정 요청 4번).

## 3. 필드 매핑 (A Adapter 출력 → B 처리 → B 출력)
A 출력 필드는 `adapter.py::_medication_record` 기준이다. "A→B"는 B가 값을 바꾸지 않고 통과시킨다는 뜻이다.

| MedicationRecord 필드 | A가 채우는 값 | B 처리 | 규칙 |
| --- | --- | --- | --- |
| `record_id` | uuid5(A 네임스페이스, `family|source_record_id`) | A→B | B가 다시 만들지 않는다 |
| `family_member_id` | 호출자 제공 | A→B | 요청과 다르면 FAILED |
| `source_type` | `PRESCRIPTION`/`MEDICINE_BAG`/`SUPPLEMENT` | A→B | `HIRA`로 바꾸지 않는다 |
| `source_record_id` | `{source_document_id}:{index}` | A→B | 문서 ID에 종속 (재업로드 정책 결정 요청 2번) |
| `record_date` | 호출자 제공 | A→B | B가 추측·변경하지 않는다 |
| `dispensing_date`, `prescribing_institution`, `dispensing_institution` | `null` | A→B | HIRA 전용 필드, 채우지 않는다 |
| `product_name_raw` | AI가 읽은 원본 | A→B | 덮어쓰지 않는다. 없으면 FAILED |
| `product_name_normalized` | `null` | **B가 채움** | 단일 매칭이면 공식 제품명, 아니면 규칙 정규화명 (HIRA 경로와 동일 규칙) |
| `drug_code`, `drug_category` | `null` | A→B | AI는 약품코드가 없다. 코드 매칭 없이 이름 매칭만 사용 |
| `unit`, `dose_per_administration`, `administrations_per_day`, `duration_days`, `dosage_text_raw` | AI가 읽은 값(Decimal은 문자열) | A→B | 문자열·null 그대로. `0`과 `null` 구분 유지. 1회량과 제품 함량을 섞지 않는다 |
| `mfds_product_id` | `null` | **B가 채움** | 단일 매칭일 때만. 복수 후보·미매칭이면 `null` |
| `ingredients[].ingredient_name_raw` | AI가 읽은 성분명 | A→B | 덮어쓰지 않는다 |
| `ingredients[].ingredient_name_normalized` | `null` | **B가 채움** | 규칙 정규화(`normalize_name`)만. 공식 성분과 같다고 확정하지 않는다 |
| `ingredients[].product_strength`, `_unit` | AI가 읽은 값(문자열) | A→B | 임의로 채우거나 바꾸지 않는다. `null` 유지 |
| `ingredients[].official_ingredient_id` | `null` | 원칙적으로 `null` 유지 | 성분이 **비어 있을 때** 공식 성분을 채우는 경우에만 응답에 있는 ID 사용(`raw`는 `null`) |
| `confidence` | AI 신뢰도(문자열) 또는 `null` | A→B | 변경하지 않는다 |
| `user_confirmed` | 항상 `false` | A→B | **B가 `true`로 바꾸지 않는다** |

B 출력의 `match`(`source`, `official_id`, `match_method`)는 기존 매처 규칙 그대로이며, 미매칭·FAILED는 모두 `null`이다.

## 4. `user_confirmed=false` 연결 경계와 확인 필요 조건
- A의 결과는 **AI 추출·정규화 후보**일 뿐이다. B는 매칭이 `MATCHED`여도 사용자 확인으로 취급하지 않는다. `user_confirmed`는 B가 읽기만 하고 바꾸지 않는다(이미 `true`로 들어온 값도 내리거나 올리지 않는다).
- `user_confirmed=true`가 되는 시점과 주체(사용자 확인 화면 → D/API)는 B의 책임이 아니다.
- 사용자 확인이 **필요한 조건**(B가 경고로 표시하는 항목):
  1. A가 `NEEDS_CONFIRMATION`을 준 경우(A 경고 전달)
  2. B 상태가 `PARTIAL`(복수 후보 또는 공식 성분 없음) 또는 `UNMATCHED`
  3. `ingredients`가 비어 있거나 함량이 `null`인 경우
  4. `confidence`가 `null`인 경우
- 사용자가 값을 수정하면 이전 정규화 결과는 낡은 것이므로 **다시 정규화**해야 한다(제안, 결정 요청 1번).

## 5. 진입점 함수 시그니처 (제안, 공통 계약 변경 없음)
HIRA 파서(`parse_hira_excel`, `normalize_hira_file`)는 그대로 두고 별도 진입점을 둔다.

```python
def normalize_structured_record(
    extraction_result: Mapping[str, Any],   # A ExtractionResult 1건 (status, record, warnings, errors)
    client: MfdsClient,                     # MockMfdsClient 또는 RealMfdsClient
    *,
    expected_family_member_id: str,         # 호출자가 제공. record 의 값과 다르면 FAILED
    threshold: float = 0.9,                 # 기존 config.yaml 의 fuzzy_threshold
) -> dict[str, Any]:                        # 공통 NormalizationResult (status, record, match, warnings, errors)
```
- 입력은 변경하지 않는다(복사본에 결과 기록). 예외 대신 `FAILED`/`UNMATCHED` 결과로 반환한다.
- 배치는 `[normalize_structured_record(r, ...) for r in results]`로 호출 측이 반복한다(A는 약 1개당 결과 1건을 준다).
- 내부 재사용: `matcher.match`(이름 매칭), `name_normalizer.normalize_name`, `adapter.to_error_detail`, `adapter.validate_common_result`. 새 의존성 없음.
- **위치와 연결(팀장 통합본과의 중복 방지)**: 이 시그니처는 제안이며 구현·통합은 팀장 확인 후 진행한다. 프로토타입은 테스트 파일 안에만 있다.

## 6. Mock 기반 테스트 시나리오와 실행 여부
파일: `tests/test_structured_input_design.py`. 모두 MockMfdsClient와 가상 데이터를 사용했다.

| # | 시나리오 | 확인 내용 | 실제 실행 |
| --- | --- | --- | --- |
| S1 | 일치 | MATCHED, 단일 `mfds_product_id`, 원본 제품명·`user_confirmed=false`·`confidence` 보존 | 실행 PASS |
| S2 | 미일치 | UNMATCHED, record·원본 보존, match 전부 null, 경고 | 실행 PASS |
| S3 | 복수 후보 | PARTIAL, `mfds_product_id`/`official_id` null, 후보 수 경고 | 실행 PASS |
| S4 | 성분 누락 + 공식 성분 있음 | 공식 성분 채움(raw=null, 함량 null 유지, 공식 성분 ID는 응답값) | 실행 PASS |
| S5 | 성분 누락 + 공식 성분도 없음 | PARTIAL, 성분 빈 배열 유지 | 실행 PASS |
| S6 | 제품명 누락 | FAILED, 조회 호출 0회, `REQUIRED_FIELD_MISSING`(product_name_raw) | 실행 PASS |
| S7 | 복수 성분 | 순서·함량 문자열(`"0.50"`)·null·`"0"`·단위 보존, 공식 성분 ID 미확정 | 실행 PASS |
| S8 | 가족 불일치 | FAILED, 조회 호출 0회 | 실행 PASS |
| S9 | `user_confirmed` | MATCHED여도 `false` 유지, 입력 `true`도 그대로 | 실행 PASS |
| S10 | A `FAILED` 입력 | 조회 없이 FAILED, A 오류 코드 전달 | 실행 PASS |
| S11 | A `NEEDS_CONFIRMATION` + record 없음 | FAILED, A 사유가 `errors`로 보존 | 실행 PASS |
| S12 | 보존 필드·입력 불변 | record_id, source_record_id, record_date, source_type, 수량 문자열, null, 키 순서 | 실행 PASS |
| S13 | 조회 실패 | UNMATCHED + 경고, 예외 원문(비밀값) 미노출 | 실행 PASS |
| S14 | A 경고 + B 경고 전달 | 둘 다 유지. A status는 계약에 담을 곳 없음(한계 명시) | 실행 PASS |
| S15 | 지원하지 않는 입력(None/문자열/status 이상) | 예외 없이 FAILED | 실행 PASS (3가지 입력) |

실행 명령: `python -m pytest backend/services/normalization/tests/test_structured_input_design.py -q` → 17 passed.
실제 식약처 API·실제 HIRA 파일·A 코드 실행은 **하지 않았다(미검증)**.

## 7. 미결정 계약과 팀장 결정 요청
1. **사용자 확인 타이밍**: AI 후보를 (a) 추출 직후 바로 정규화해 미리보기로 보여주고 사용자가 고치면 재정규화할지, (b) 사용자 확인 후에만 정규화할지. B 제안은 (a)+재정규화이며 어느 경우든 B는 `user_confirmed`를 바꾸지 않는다. D가 미확인 record를 비교에 쓸지도 함께 결정 필요.
2. **재업로드 ID 정책**: A의 `source_record_id`는 `{source_document_id}:{index}`라 같은 이미지를 다시 올려 문서 ID가 달라지면 ID가 달라지고, `record_id` 네임스페이스·식도 A(`family|source_record_id`)와 B(`family|source_type|source_record_id`)가 다르다. 같은 약을 A·B 경로로 각각 올렸을 때의 중복 처리와 통일 규칙이 필요하다.
3. **중복 조제 처리**: HIRA는 같은 약의 반복 조제를 보존하지만 D가 동률 후보를 매칭하지 않아 `NEEDS_CONFIRMATION`+`NEW`로 갈라진다(`d_repro/README.md` R1·R2). 대표 기록 선택/그룹 비교 책임을 D·통합 계층 중 어디에 둘지.
4. **A 상태 전달**: 계약 B에 A의 `SUCCESS`/`NEEDS_CONFIRMATION`을 담을 필드가 없다. 호출 측 봉투(envelope)로 따로 전달할지, 계약 변경(협의)할지.
5. **`NEEDS_CONFIRMATION`+record 없음의 B 상태**: 현재 설계는 `FAILED`(record null)로 매핑. 다른 표현이 필요한지.
6. **`product_name_normalized` 통일**: 공식 제품명 vs 규칙 정규화명이 시점마다 바뀔 수 있음(공통 Schema 사항).
7. **구현·통합 위치**: 진입점을 B 모듈로 둘지, 팀장 통합 브랜치(`codex/*`)에서 구현할지(중복 방지).
