# HIRA 비교 보류 계약 초안 — 미합의·미구현

> 후속 상태: 사용자 승인에 따른 TASK D MVP 구현은 [HIRA_COMPARISON_HOLD_V2.md](HIRA_COMPARISON_HOLD_V2.md)에 기록한다. 아래는 당시 초안/관찰 기록이며 팀 전체 합의 완료를 의미하지 않는다.

작성 기준: TASK D `5d54e88`, 기존 `TASK_D_POLICY_REVIEW.md` 및 실제
`backend/api/pipeline.py`, `schemas.py`, `reconciliation/b_integration.py`,
`engine.py`, B의 parser/adapter/repeat_report를 대조했다.

**이 문서는 검토안이다.** 보류 gate, 새 응답 모델, Endpoint, 대표 기록 선택을
구현하지 않는다. `docs/API_CONTRACT.md`와 기존 Reconciliation 상태·reason_code는
변경하지 않는다. 이번 실행 변경은 C 접근성 코드·브라우저 검사의 선별 반영뿐이다.

## 1. 해결하려는 실제 문제

| 실제 코드 동작 | 위험 | 제안하는 방어 위치 |
| --- | --- | --- |
| `_has_comparable_dose_change`는 한쪽 값이 null이면 변화로 보지 않고, 매칭된 기록에 고정 유지 사유를 붙일 수 있음 | 모르는 함량을 동일 함량이라고 설명 | D 호출 전 성분·함량의 비교 가능성 검사. 모르면 별도 보류, 기존 NEEDS_CONFIRMATION으로 변환 금지 |
| `_prepare_batch`는 FAILED를 review_results에 보존하지만 비교 입력에서는 제외 | 현재 실패행이 과거 약과 관련됐는데 NOT_FOUND_IN_LATEST_SOURCE로 표시할 수 있음 | 실패 원본의 식별 가능성/자료 완전성을 검사. 식별 범위를 모르면 양쪽 자료 전체 보류 |
| 동률 매칭은 회피하지만 이전 2/현재 1에서는 앞선 이전 행이 먼저 소비할 수 있음 | 입력 순서와 방향에 따라 유지/미확인 결과가 달라짐 | 양쪽 반복 그룹을 엔진 호출 전에 검사. 대표를 임의 선택하지 않고 전체 보류 |
| FAILED의 공통 record는 null이고 내부 raw_row/source_ref는 공통 adapter에서 빠짐 | 어떤 원본 행을 고쳐야 하는지 표시하기 어려움 | 공통 record 바깥의 출처 참조·허용된 raw snapshot 보존 |

`MAINTAINED/SAME_INGREDIENT_SAME_STRENGTH`와
`NEEDS_CONFIRMATION/NOT_FOUND_IN_LATEST_SOURCE`의 의미를 완화·확장해서 해결하지 않는다.
비교 불가와 최신 자료에서의 미확인은 다른 사실이다.

## 2. 최소 권장 구조: 결과 바깥에 실행 정보와 원본 참조

기존 HIRA 응답의 `processing`, `accepted_results`, `review_results`는 유지한다.
다음 세 필드와 한 nullable 변경을 **별도 응답 버전 또는 명시적 opt-in**에 제안한다.
어떤 URL/버전/opt-in을 사용할지는 결정 사항이며 현재 Endpoint는 그대로 둔다.

| 항목 | 초안 | 의미 |
| --- | --- | --- |
| `family_member_id` 추가 | UUID | 보류라서 비교 결과가 null이어도 가족 범위를 확인 |
| `comparison` 추가 | `{executed: boolean, holds: Hold[]}` | 비교 엔진이 실행됐는지, 왜 실행되지 않았는지 |
| `source_rows` 추가 | `SourceRow[]` | 원본 위치/허용된 raw 값과 NormalizationResult의 연결 |
| `reconciliation_result` nullable | 기존 결과 또는 null | 보류면 null. 실행됐다면 기존 Contract D 그대로 |

`Hold = {kind, message, affected_refs}`. `kind`는 실행 진단용 새 이름이며
공통 `ErrorDetail.code`나 Reconciliation `reason_code`가 아니다. 예시 이름도
아직 미확정이다: `UNIDENTIFIED_FAILED_INPUT`, `UNKNOWN_COMPARISON_FIELDS`,
`AMBIGUOUS_REPEATED_RECORDS`.

`SourceRef = {side, document_id, input_index}`:

- side는 previous/current, document_id는 시스템이 요청 문서에 부여한 UUID다.
- input_index는 공통 결과를 accepted/review로 나누기 전의 0-based 순번이다.
  실패 결과도 순번이 있으므로 record_id를 만들어 끼워 넣지 않는다.
- `SourceRow = {ref, locator, raw_fields, normalization_ref}`.
  locator는 확인 가능한 sheet_index/row만 사용한다. 알 수 없으면 null이다.
- normalization_ref는 해당 응답의 `/accepted_results/previous/0` 같은 JSON Pointer다.
  `FAILED`는 `/review_results/current/0`을 가리킨다. 참조 대상은 원본 그대로인
  기존 NormalizationResult이며 내부에 새 필드를 넣지 않는다.
- 파일/헤더 전체 오류에는 실제 행 번호를 추측하지 않는다. 결과가 있는 파일 오류는
  그 결과 순번과 null locator를 쓴다. 결과조차 없는 빈 자료의 표현은 승인 시
  별도로 정하며, 가짜 MedicationRecord/NormalizationResult를 만들지 않는다.
- 이 참조는 요청 내 추적용이다. 재업로드 중복 식별자, 인증 수단 또는 DB ID가 아니다.

현재 B 내부 `MedicationRecord`에는 `raw_row`와 `source_ref={file,sheet,row}`가 있다.
미래 구현에서는 **공통 adapter 전** 이 정보를 요청 문서 UUID/결과 순번에 연결하고,
분류 후 normalization_ref를 연결해야 한다. 이미 record:null로 변환된 결과만으로
원본을 역추측해서는 안 된다. 파일명·임시 경로·불필요한 시트명은 응답에 복사하지 않는다.
raw_fields는 검토에 필요한 약품/조제/수량 필드만 허용하고 개인정보 열을 추가 수집하지 않는다.
이번에는 가상 예시뿐이며 영구 저장·로그·DB·실제 자료 업로드를 추가하지 않는다.

## 3. 실행/보류 불변 조건 (전부 제안)

1. `executed=false`면 holds가 비어 있지 않고, `reconciliation_result=null`,
   `current_intake_states=[]`다. 이는 약이 없다는 뜻도, 기존 복용 확인을 지우라는
   뜻도 아니다. 새 비교/복용 상태를 만들지 않았다는 뜻이다.
2. `executed=true`면 holds는 빈 배열이고 기존 Contract D 결과를 그대로 반환한다.
   정당하게 빈 결과인 경우와 비교를 하지 않은 경우를 null/실행 flag로 구분한다.
3. 최소안은 **어느 한 사유라도 있으면 양쪽 자료 전체 보류**다. 영향 범위를
   특정할 수 없는 실패행이면 affected_refs에 양쪽 전체 원본 참조를 넣고 설명한다.
4. 성분/함량/단위 또는 제품 대응이 불명확하면 알려진 수량 변화만으로 나머지
   미확인 정보를 덮지 않는다. 정확한 비교 가능 조건은 승인 대상이며 보간·단위
   환산·성분만으로 제품 동일성 확정을 새로 만들지 않는다.
5. 반복 여부는 양쪽 전체를 검사한 후 결정한다. 입력 배열을 임의 정렬하거나
   최신 행을 대표로 골라 기존 greedy match에 넣는 우회는 하지 않는다.
6. accepted_results는 기존 비실패 정규화 결과, review_results는 기존 FAILED를
   보존한다. 보류라고 PARTIAL/UNMATCHED/MATCHED를 FAILED로 바꾸지 않는다.
   보류 사유는 오직 comparison.holds에 둔다.
7. 예상되는 비교 보류는 파싱·정규화 성공 후의 도메인 상태이므로 HTTP 200을
   제안한다. 손상 파일/형식·크기·가족 오류의 기존 400/413/415/422는 별도 유지한다.
8. message는 사용자용 고정 설명을 사용한다. SDK 예외·비밀값·내부 경로를 반영하지 않는다.

## 4. 가상 입력과 출력

아래 입력은 HTTP 업로드 요청이 아니라 **B 공통 결과 분류 직후 D 실행 판단에
전달할 내부 입력의 초안**이다. HTTP 입력은 기존 previous/current XLSX 역할을
유지하는 안이다. 모든 이름·ID·수량은 가상이다. 이전의 알려진 함량은 이 가상
정규화 입력의 전제이며 실제 HIRA/식약처 검증을 의미하지 않는다.

### 4.1 이전 정상 1건 + 현재 식별 불가 실패 1건

입력:

```json
{
  "family_member_id": "00000000-0000-4000-8000-000000000001",
  "accepted_results": {
    "previous": [
      {
        "status": "MATCHED",
        "record": {
          "record_id": "20000000-0000-4000-8000-000000000001",
          "family_member_id": "00000000-0000-4000-8000-000000000001",
          "source_type": "HIRA",
          "source_record_id": "virtual-hira-previous-001",
          "record_date": "2026-09-01",
          "dispensing_date": "2026-09-01",
          "prescribing_institution": null,
          "dispensing_institution": null,
          "product_name_raw": "가상알파정",
          "product_name_normalized": "가상알파정",
          "drug_code": "000000001",
          "drug_category": null,
          "unit": "정",
          "dose_per_administration": "1",
          "administrations_per_day": "2",
          "duration_days": "7",
          "dosage_text_raw": null,
          "mfds_product_id": "virtual-alpha",
          "ingredients": [
            {
              "ingredient_name_raw": "가상알파성분",
              "ingredient_name_normalized": "가상알파성분",
              "product_strength": "100",
              "product_strength_unit": "mg",
              "official_ingredient_id": null
            }
          ],
          "confidence": null,
          "user_confirmed": false
        },
        "match": {
          "source": "LOCAL_MOCK",
          "official_id": "virtual-alpha",
          "match_method": "CODE_EXACT"
        },
        "warnings": [],
        "errors": []
      }
    ],
    "current": []
  },
  "review_results": {
    "previous": [],
    "current": [
      {
        "status": "FAILED",
        "record": null,
        "match": {
          "source": null,
          "official_id": null,
          "match_method": null
        },
        "warnings": [],
        "errors": [
          {
            "code": "NORMALIZATION_FAILED",
            "message": "가상 행의 조제일자와 제품명을 확인할 수 없습니다.",
            "field": "record_date"
          }
        ]
      }
    ]
  },
  "source_rows": [
    {
      "ref": {
        "side": "previous",
        "document_id": "10000000-0000-4000-8000-000000000001",
        "input_index": 0
      },
      "locator": {
        "sheet_index": 1,
        "row": 3
      },
      "raw_fields": {
        "product_name": "가상알파정",
        "dispensing_date": "2026-09-01",
        "drug_code": "000000001"
      },
      "normalization_ref": "/accepted_results/previous/0"
    },
    {
      "ref": {
        "side": "current",
        "document_id": "10000000-0000-4000-8000-000000000002",
        "input_index": 0
      },
      "locator": {
        "sheet_index": 1,
        "row": 3
      },
      "raw_fields": {
        "product_name": null,
        "dispensing_date": "가상 오류값",
        "drug_code": null
      },
      "normalization_ref": "/review_results/current/0"
    }
  ]
}
```

제안 출력 (기존 정규화 결과·원본 snapshot을 그대로 보존):

```json
{
  "family_member_id": "00000000-0000-4000-8000-000000000001",
  "accepted_results": {
    "previous": [
      {
        "status": "MATCHED",
        "record": {
          "record_id": "20000000-0000-4000-8000-000000000001",
          "family_member_id": "00000000-0000-4000-8000-000000000001",
          "source_type": "HIRA",
          "source_record_id": "virtual-hira-previous-001",
          "record_date": "2026-09-01",
          "dispensing_date": "2026-09-01",
          "prescribing_institution": null,
          "dispensing_institution": null,
          "product_name_raw": "가상알파정",
          "product_name_normalized": "가상알파정",
          "drug_code": "000000001",
          "drug_category": null,
          "unit": "정",
          "dose_per_administration": "1",
          "administrations_per_day": "2",
          "duration_days": "7",
          "dosage_text_raw": null,
          "mfds_product_id": "virtual-alpha",
          "ingredients": [
            {
              "ingredient_name_raw": "가상알파성분",
              "ingredient_name_normalized": "가상알파성분",
              "product_strength": "100",
              "product_strength_unit": "mg",
              "official_ingredient_id": null
            }
          ],
          "confidence": null,
          "user_confirmed": false
        },
        "match": {
          "source": "LOCAL_MOCK",
          "official_id": "virtual-alpha",
          "match_method": "CODE_EXACT"
        },
        "warnings": [],
        "errors": []
      }
    ],
    "current": []
  },
  "review_results": {
    "previous": [],
    "current": [
      {
        "status": "FAILED",
        "record": null,
        "match": {
          "source": null,
          "official_id": null,
          "match_method": null
        },
        "warnings": [],
        "errors": [
          {
            "code": "NORMALIZATION_FAILED",
            "message": "가상 행의 조제일자와 제품명을 확인할 수 없습니다.",
            "field": "record_date"
          }
        ]
      }
    ]
  },
  "source_rows": [
    {
      "ref": {
        "side": "previous",
        "document_id": "10000000-0000-4000-8000-000000000001",
        "input_index": 0
      },
      "locator": {
        "sheet_index": 1,
        "row": 3
      },
      "raw_fields": {
        "product_name": "가상알파정",
        "dispensing_date": "2026-09-01",
        "drug_code": "000000001"
      },
      "normalization_ref": "/accepted_results/previous/0"
    },
    {
      "ref": {
        "side": "current",
        "document_id": "10000000-0000-4000-8000-000000000002",
        "input_index": 0
      },
      "locator": {
        "sheet_index": 1,
        "row": 3
      },
      "raw_fields": {
        "product_name": null,
        "dispensing_date": "가상 오류값",
        "drug_code": null
      },
      "normalization_ref": "/review_results/current/0"
    }
  ],
  "processing": {
    "parser": "DETERMINISTIC",
    "file_processing": "EXECUTED",
    "official_data_mode": "LOCAL_MOCK",
    "persisted": false
  },
  "comparison": {
    "executed": false,
    "holds": [
      {
        "kind": "UNIDENTIFIED_FAILED_INPUT",
        "message": "현재 실패행의 제품을 식별할 수 없어 양쪽 자료 전체 비교를 실행하지 않았습니다.",
        "affected_refs": [
          {
            "side": "previous",
            "document_id": "10000000-0000-4000-8000-000000000001",
            "input_index": 0
          },
          {
            "side": "current",
            "document_id": "10000000-0000-4000-8000-000000000002",
            "input_index": 0
          }
        ]
      }
    ]
  },
  "reconciliation_result": null,
  "current_intake_states": []
}
```

이 경우 과거 약을 NOT_FOUND_IN_LATEST_SOURCE로 만들지 않는다. 현재 실패행이
그 약인지 아닌지 알 수 없으므로 영향을 양쪽 전체로 잡는다.

### 4.2 성분/함량 미확인

입력이 모두 비실패여도 어느 대응 기록에 product_strength 또는 비교할 성분이
없다면 다음 실행 정보와 null 결과를 제안한다. accepted_results와 source_rows는
원본 그대로 유지하고, review_results를 비실패 자료로 채우지 않는다.

```json
{
  "comparison": {
    "executed": false,
    "holds": [{
      "kind": "UNKNOWN_COMPARISON_FIELDS",
      "message": "성분 또는 함량을 확인할 수 없어 비교를 실행하지 않았습니다.",
      "affected_refs": [
        {"side":"previous","document_id":"10000000-0000-4000-8000-000000000001","input_index":0},
        {"side":"current","document_id":"10000000-0000-4000-8000-000000000002","input_index":0}
      ]
    }]
  },
  "reconciliation_result": null,
  "current_intake_states": []
}
```

위 JSON은 실행 정보 부분의 투영이며 완전한 응답의 생략 필드를 새로 정의하지 않는다.

### 4.3 반복 기록과 입력 순서

이전 2건/현재 1건, 이전 1건/현재 2건, 양쪽 2건에서 같은 신뢰 제품 식별자로
동률 후보가 생기는 가상 입력은 `AMBIGUOUS_REPEATED_RECORDS`로 전체 보류하는 안이다.
원본 순서를 바꾸어도 실행 여부·보류 사유·영향 참조 **집합**이 같아야 한다.
표시 순서는 결정적이어도 원본 input_index와 raw snapshot을 변경하지 않는다.
대표 선택은 하지 않는다. 성분만 같은 서로 다른 제품은 이 이유로 자동 병합하지 않는다.

### 4.4 실행 가능한 입력

양쪽 전체가 합의된 비교 가능 조건을 만족하면 `comparison={"executed":true,"holds":[]}`와
기존 Contract D를 반환한다. 기존 상태/사유를 확장하지 않고, Current Intake는
기존 UNKNOWN/PENDING에서 시작한다. 비교 결과 확인과 실제 복용 여부 확인은 분리한다.

## 5. 부분 보류는 최소안에 포함하지 않는다

문제 현재 후보만 제외하면 그 상대 과거 기록이 잘못된 미확인으로 바뀔 수 있다.
그룹 부분 보류를 허용하려면 신뢰 ID, 충돌 처리, 이전/현재 연결 범위와 입력
완전성, 비교한 집합/보류한 집합의 원본 참조를 추가로 합의해야 한다.
그때도 연결된 양쪽 그룹을 함께 제외해야 하며 record:null로 정체를 모르는 행이
있으면 전체 영향을 배제할 수 없다. 현재 API에서 부분 실행을 암묵적으로 추가하지 않는다.

## 6. 승인해야 할 결정과 이후 검증

- 실행 정보의 이름과 Hold 종류, 새 응답 버전/opt-in, top-level 가족 범위 및 null 허용.
- 성분·함량·단위·제품 식별의 최소 비교 가능 조건과 빈 자료/파일 수준 오류 표현.
- 우선 전체 보류를 쓸지, 추후 그룹 부분 보류를 별도 단계로 검토할지.
- 원본 필드 허용 목록, 출처 참조 수명과 반환 범위. 영구 저장은 이번 범위 밖이다.
- 반복 그룹/대표 선택 및 재업로드 중복 처리는 별도 결정으로 남긴다.

승인 후에는 정상 실행, unknown strength/성분, 현재/이전 일부 실패, 반복 입력
방향·순서 교환, 원본 불변, null 결과와 빈 결과 구분, raw 참조 해소, UNKNOWN/PENDING
초기화, 기존 HIRA·사진 회귀를 검증한다. 실패/반복 원본을 제거하는 방식으로 통과시키지 않는다.

현재 `VerticalSliceResponse`는 extra=forbid이며 reconciliation_result는 non-null이다.
따라서 이 초안을 기존 Endpoint에 곧바로 넣으면 기존 validator/클라이언트와 충돌한다.
승인 전까지 backend/frontend 응답 처리, 비교 gate, 대표 선택 코드는 수정하지 않는다.
