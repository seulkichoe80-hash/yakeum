# API Contract v1 Draft

이 문서는 실제 서버 Endpoint 구현 명세가 아니라 TASK A/B/C/D가 병렬 개발하기 위한 **팀 간 데이터 계약 초안**이다. HTTP Endpoint, Method, 인증 방식, Framework는 아직 확정하지 않는다.

연결 흐름은 다음과 같다.

TASK A 비정형 자료 → `ExtractionResult` → TASK B 정규화·공식 데이터 매칭 → `NormalizationResult` → TASK D Reconciliation → `ReconciliationResult` → TASK C 사용자 화면

## 1. Single Source of Truth

- `MedicationRecord`와 `Ingredient` 구조는 `docs/DATA_SCHEMA.md`의 **MedicationRecord Schema v1 Draft**를 유일한 기준으로 사용한다.
- 이 문서에서 별도의 MedicationRecord 구조를 새로 정의하지 않는다.
- Schema 변경 필요성이 발견되면 Contract에서 임의 필드로 우회하지 않고 TODO로 보고한다.
- 날짜 필드는 `YYYY-MM-DD` 형식을 사용한다.
- `drug_code`는 String으로 전달하여 선행 0과 원래 표현을 보존한다.
- Decimal은 float 정밀도 손실을 피한다. 전송 표현은 팀 합의 전까지 정밀도를 보존할 수 있는 문자열을 우선 사용한다.
- `null`은 미확인, 원본에 없음 또는 미매칭을 뜻하며 `0`, `false`, `""`, `unknown` 문자열과 구분한다.
- raw 값은 normalized 값으로 덮어쓰지 않는다.
- 모든 예시는 가상 데이터이며 실제 개인정보나 건강정보를 사용하지 않는다.
- AI 결과와 안전정보를 자동 확정하거나 의료적 판단에 사용하지 않는다.

`warnings`와 `errors`는 배열이며, 항목이 없으면 빈 배열 `[]`을 사용한다. 오류 항목은 이 문서의 `ErrorDetail` Draft를 따른다.

## 2. Contract A: ExtractionResult

### 목적

TASK A가 약봉투, 처방전, 건강기능식품 등 비정형 입력을 Multimodal AI로 분석한 결과를 공통 시스템에 전달한다.

### 구조

```json
{
  "status": "SUCCESS | NEEDS_CONFIRMATION | FAILED",
  "record": null,
  "warnings": [],
  "errors": []
}
```

`record`는 `MedicationRecord | null`이다. 성공 또는 사용자 확인이 필요한 경우 `docs/DATA_SCHEMA.md`를 따르는 MedicationRecord를 전달할 수 있다.

### 상태 의미

| 상태 | 의미 |
| --- | --- |
| `SUCCESS` | 최소 계약을 충족하는 후보를 추출했지만 사용자 확인 전에는 확정하지 않음 |
| `NEEDS_CONFIRMATION` | 불확실하거나 누락된 값이 있어 사용자 확인·수정이 필요함 |
| `FAILED` | 입력을 MedicationRecord 후보로 만들 수 없음. `record`는 `null` |

### 규칙

- AI 결과의 `user_confirmed` 기본값은 `false`다.
- `confidence`는 DATA_SCHEMA v1 Draft의 record-level confidence를 따른다.
- AI가 알 수 없는 값은 추측해 채우지 않고 `null`로 둔다.
- `ingredients`의 빈 배열 허용 여부는 DATA_SCHEMA TODO가 확정될 때까지 자동 보정하지 않는다.
- AI는 `mfds_product_id`, 공식 성분 ID, DUR, 안전성 근거를 임의 생성하지 않는다.
- 원본에서 읽은 raw 값은 정규화된 것처럼 바꾸지 않는다.

## 3. Contract B: NormalizationResult

### 목적

TASK B가 HIRA deterministic parser 결과 또는 식약처 공식 데이터 정규화 결과를 공통 시스템에 전달한다.

### 구조

```json
{
  "status": "MATCHED | PARTIAL | UNMATCHED | FAILED",
  "record": null,
  "match": {
    "source": null,
    "official_id": null,
    "match_method": null
  },
  "warnings": [],
  "errors": []
}
```

`record`는 `MedicationRecord | null`이다. `match`의 세부 Enum과 공식 근거 연결 방식은 아직 확정하지 않는다.

### 상태 의미

| 상태 | 의미 |
| --- | --- |
| `MATCHED` | 공식 데이터의 단일 결과에 매칭됨 |
| `PARTIAL` | 일부 필드만 매칭되었거나 복수 후보 확인이 필요함 |
| `UNMATCHED` | 공식 데이터에서 일치 결과를 찾지 못했지만 원본 record는 유지함 |
| `FAILED` | parsing 또는 normalization을 수행할 수 없음 |

### 규칙

- HIRA Excel은 AI가 아니라 deterministic parser로 처리한다.
- 공식 데이터 매칭에 실패해도 원본 MedicationRecord를 삭제하지 않는다.
- raw 값은 항상 유지한다.
- normalized 값이 확정되지 않으면 `null`을 허용한다.
- `drug_code`는 String으로 유지한다.
- `product_strength`와 `dose_per_administration`을 서로 대체하지 않는다.
- 공식 정보의 출처와 매칭 방법을 확인할 수 있어야 하며, 값을 임의 생성하지 않는다.

## 4. Contract D: ReconciliationResult

### 목적

TASK D가 MedicationRecord의 과거와 현재를 비교한 결과를 TASK C Frontend에 전달한다.

### 구조

```json
{
  "family_member_id": "",
  "generated_at": "",
  "items": [
    {
      "status": "MAINTAINED | NEW | DOSE_CHANGED | NEEDS_CONFIRMATION",
      "previous_record": null,
      "current_record": null,
      "reason_code": "",
      "evidence": []
    }
  ]
}
```

`previous_record`와 `current_record`는 각각 `MedicationRecord | null`이다. `generated_at`은 결과 생성 시각이며 정확한 timezone·직렬화 정책은 TODO다. `evidence`는 향후 공식 근거 구조가 확정될 때까지 빈 배열을 허용한다.

### 상태와 reason_code

| 상태 | reason_code | 시스템 비교 의미 |
| --- | --- | --- |
| `MAINTAINED` | `SAME_INGREDIENT_SAME_STRENGTH` | 동일 성분과 동일 제품 함량이 지속됨 |
| `NEW` | `NEW_RECORD` | 이전 기록 없이 현재 자료에 존재함 |
| `DOSE_CHANGED` | `STRENGTH_OR_DOSAGE_CHANGED` | 제품 함량 또는 투약 관련 값의 변화가 확인됨 |
| `NEEDS_CONFIRMATION` | `NOT_FOUND_IN_LATEST_SOURCE` | 과거 기록이 최신 자료에서 확인되지 않아 사용자 확인이 필요함 |

### 규칙

- 최신 자료에서 확인되지 않았다는 이유만으로 복용중단 상태를 만들지 않는다. 이 경우 `NEEDS_CONFIRMATION`을 사용한다.
- `reason_code`는 의료적 판단 문장이 아니라 시스템 비교 이유를 나타내는 deterministic code다.
- `product_strength` 변화와 `dose_per_administration` 변화는 별도로 비교한다.
- 두 변화의 세부 상태 분리는 DATA_SCHEMA TODO이므로 현재 새로운 Reconciliation 상태를 추가하지 않는다.
- Frontend는 이 결과를 표시하며 자체 Reconciliation 판정 로직을 만들지 않는다.

## 5. Frontend 개발용 ReconciliationResult Mock

아래 예시는 TASK C가 Backend 완성을 기다리지 않고 화면을 개발하기 위한 가상 데이터다. 제품명, 성분명, 기관명 및 ID는 모두 실제 개인이나 실제 복용기록과 관계없는 테스트 값이다. 별도 Mock JSON 파일은 이번 단계에서 만들지 않는다.

```json
{
  "family_member_id": "00000000-0000-4000-8000-000000000001",
  "generated_at": "2026-10-01T00:00:00Z",
  "items": [
    {
      "status": "MAINTAINED",
      "previous_record": {
        "record_id": "10000000-0000-4000-8000-000000000001",
        "family_member_id": "00000000-0000-4000-8000-000000000001",
        "source_type": "HIRA",
        "source_record_id": "virtual-hira-previous-001",
        "record_date": "2026-08-01",
        "dispensing_date": "2026-08-01",
        "prescribing_institution": "가상의원",
        "dispensing_institution": "가상약국",
        "product_name_raw": "가상제품A 100mg",
        "product_name_normalized": "가상제품A",
        "drug_code": "000000001",
        "drug_category": "가상분류",
        "unit": "정",
        "dose_per_administration": "1",
        "administrations_per_day": "1",
        "duration_days": "30",
        "dosage_text_raw": null,
        "mfds_product_id": "VIRTUAL-PRODUCT-A",
        "ingredients": [
          {
            "ingredient_name_raw": "가상성분A",
            "ingredient_name_normalized": "가상성분A",
            "product_strength": "100",
            "product_strength_unit": "mg",
            "official_ingredient_id": "VIRTUAL-INGREDIENT-A"
          }
        ],
        "confidence": null,
        "user_confirmed": true
      },
      "current_record": {
        "record_id": "10000000-0000-4000-8000-000000000002",
        "family_member_id": "00000000-0000-4000-8000-000000000001",
        "source_type": "HIRA",
        "source_record_id": "virtual-hira-current-001",
        "record_date": "2026-09-01",
        "dispensing_date": "2026-09-01",
        "prescribing_institution": "가상의원",
        "dispensing_institution": "가상약국",
        "product_name_raw": "가상제품A 100mg",
        "product_name_normalized": "가상제품A",
        "drug_code": "000000001",
        "drug_category": "가상분류",
        "unit": "정",
        "dose_per_administration": "1",
        "administrations_per_day": "1",
        "duration_days": "30",
        "dosage_text_raw": null,
        "mfds_product_id": "VIRTUAL-PRODUCT-A",
        "ingredients": [
          {
            "ingredient_name_raw": "가상성분A",
            "ingredient_name_normalized": "가상성분A",
            "product_strength": "100",
            "product_strength_unit": "mg",
            "official_ingredient_id": "VIRTUAL-INGREDIENT-A"
          }
        ],
        "confidence": null,
        "user_confirmed": true
      },
      "reason_code": "SAME_INGREDIENT_SAME_STRENGTH",
      "evidence": []
    },
    {
      "status": "NEW",
      "previous_record": null,
      "current_record": {
        "record_id": "20000000-0000-4000-8000-000000000001",
        "family_member_id": "00000000-0000-4000-8000-000000000001",
        "source_type": "PRESCRIPTION",
        "source_record_id": "virtual-prescription-001",
        "record_date": "2026-09-02",
        "dispensing_date": null,
        "prescribing_institution": "가상병원",
        "dispensing_institution": null,
        "product_name_raw": "가상제품B",
        "product_name_normalized": "가상제품B",
        "drug_code": null,
        "drug_category": null,
        "unit": "캡슐",
        "dose_per_administration": "1",
        "administrations_per_day": "2",
        "duration_days": "7",
        "dosage_text_raw": "하루 두 번 한 캡슐",
        "mfds_product_id": null,
        "ingredients": [
          {
            "ingredient_name_raw": "가상성분B",
            "ingredient_name_normalized": "가상성분B",
            "product_strength": "50",
            "product_strength_unit": "mg",
            "official_ingredient_id": null
          }
        ],
        "confidence": "0.91",
        "user_confirmed": false
      },
      "reason_code": "NEW_RECORD",
      "evidence": []
    },
    {
      "status": "DOSE_CHANGED",
      "previous_record": {
        "record_id": "30000000-0000-4000-8000-000000000001",
        "family_member_id": "00000000-0000-4000-8000-000000000001",
        "source_type": "MEDICINE_BAG",
        "source_record_id": "virtual-bag-previous-001",
        "record_date": "2026-08-10",
        "dispensing_date": "2026-08-10",
        "prescribing_institution": null,
        "dispensing_institution": "가상약국",
        "product_name_raw": "가상제품C 100mg",
        "product_name_normalized": "가상제품C",
        "drug_code": null,
        "drug_category": null,
        "unit": "정",
        "dose_per_administration": "1",
        "administrations_per_day": "1",
        "duration_days": "14",
        "dosage_text_raw": "하루 한 번 한 정",
        "mfds_product_id": null,
        "ingredients": [
          {
            "ingredient_name_raw": "가상성분C",
            "ingredient_name_normalized": "가상성분C",
            "product_strength": "100",
            "product_strength_unit": "mg",
            "official_ingredient_id": null
          }
        ],
        "confidence": "0.88",
        "user_confirmed": true
      },
      "current_record": {
        "record_id": "30000000-0000-4000-8000-000000000002",
        "family_member_id": "00000000-0000-4000-8000-000000000001",
        "source_type": "MEDICINE_BAG",
        "source_record_id": "virtual-bag-current-001",
        "record_date": "2026-09-10",
        "dispensing_date": "2026-09-10",
        "prescribing_institution": null,
        "dispensing_institution": "가상약국",
        "product_name_raw": "가상제품C 200mg",
        "product_name_normalized": "가상제품C",
        "drug_code": null,
        "drug_category": null,
        "unit": "정",
        "dose_per_administration": "1",
        "administrations_per_day": "1",
        "duration_days": "14",
        "dosage_text_raw": "하루 한 번 한 정",
        "mfds_product_id": null,
        "ingredients": [
          {
            "ingredient_name_raw": "가상성분C",
            "ingredient_name_normalized": "가상성분C",
            "product_strength": "200",
            "product_strength_unit": "mg",
            "official_ingredient_id": null
          }
        ],
        "confidence": "0.9",
        "user_confirmed": true
      },
      "reason_code": "STRENGTH_OR_DOSAGE_CHANGED",
      "evidence": []
    },
    {
      "status": "NEEDS_CONFIRMATION",
      "previous_record": {
        "record_id": "40000000-0000-4000-8000-000000000001",
        "family_member_id": "00000000-0000-4000-8000-000000000001",
        "source_type": "SUPPLEMENT",
        "source_record_id": "virtual-supplement-001",
        "record_date": "2026-08-15",
        "dispensing_date": null,
        "prescribing_institution": null,
        "dispensing_institution": null,
        "product_name_raw": "가상건강제품D",
        "product_name_normalized": "가상건강제품D",
        "drug_code": null,
        "drug_category": null,
        "unit": "캡슐",
        "dose_per_administration": "1",
        "administrations_per_day": "1",
        "duration_days": null,
        "dosage_text_raw": "하루 한 캡슐",
        "mfds_product_id": null,
        "ingredients": [
          {
            "ingredient_name_raw": "가상기능성원료D",
            "ingredient_name_normalized": "가상기능성원료D",
            "product_strength": "10",
            "product_strength_unit": "mg",
            "official_ingredient_id": null
          }
        ],
        "confidence": "0.86",
        "user_confirmed": true
      },
      "current_record": null,
      "reason_code": "NOT_FOUND_IN_LATEST_SOURCE",
      "evidence": []
    }
  ]
}
```

## 6. Error Contract Draft

팀별로 서로 다른 오류 형식을 만들지 않도록 `warnings`와 `errors`의 항목을 다음 구조로 맞춘다.

```json
{
  "code": "REQUIRED_FIELD_MISSING",
  "message": "필수 입력값을 확인할 수 없습니다.",
  "field": "product_name_raw"
}
```

`field`는 특정 필드와 관계없는 오류라면 `null`이다. `message`에는 진단, 처방, 복용량 변경, 복용 중단 또는 안전성 최종 판단 같은 의료적 판단을 넣지 않는다.

초기 공통 오류 코드:

- `INVALID_FILE_FORMAT`
- `REQUIRED_FIELD_MISSING`
- `AI_EXTRACTION_FAILED`
- `OFFICIAL_MATCH_NOT_FOUND`
- `NORMALIZATION_FAILED`

오류 코드 추가가 필요하면 팀 간 중복과 의미를 확인한 뒤 이 문서에서 협의한다.

## 7. TODO: 아직 확정하지 않는 사항

- 실제 HTTP Endpoint URL
- GET/POST/PATCH 등 HTTP Method
- 인증 방식
- 가족 권한관리 방식
- DB ID 생성 방식
- Pagination
- Evidence 최종 구조
- 사용자 수정이력 API
- 파일 업로드 방식
- HTTP status code 정책
- 실제 Backend Framework
- `generated_at` timezone 및 직렬화 방식
- `match.source`, `match_method`의 허용값
- Contract 버전 관리 방식

## 8. 팀 간 의존성과 병렬 개발 기준

- TASK A는 TASK B 완료를 기다리지 않는다. `ExtractionResult` Contract를 기준으로 개발한다.
- TASK B는 TASK A 완료를 기다리지 않는다. `docs/DATA_SCHEMA.md`의 MedicationRecord Contract를 기준으로 개발한다.
- TASK C는 Backend 완료를 기다리지 않는다. 이 문서의 `ReconciliationResult` Mock Contract로 개발한다.
- TASK D는 TASK A/B 완료를 기다리지 않는다. 가상 MedicationRecord로 Reconciliation Engine을 개발한다.
- 통합 시점에는 모든 담당자가 동일한 `docs/DATA_SCHEMA.md`와 `docs/API_CONTRACT.md`를 기준으로 연결한다.

이 문서는 **API Contract v1 Draft**이며 실제 Endpoint나 Backend 구현을 확정하지 않는다. 변경이 필요하면 모든 담당자가 영향 범위를 확인하고 합의한 뒤 수정한다.


## TASK D MVP HIRA 응답 버전 (통합안)

사용자가 승인한 TASK D MVP 범위로 `/api/v2/reconciliations/hira`를 추가했다.
이는 팀 전체 계약 합의 완료를 뜻하지 않는다. v1 응답과 MedicationRecord,
Reconciliation 상태·reason_code 의미는 유지한다. 새 TASK D 화면만 v2를 사용한다.
실행 여부·전체 보류 사유·원본 참조와 nullable 결과 계약은
[HIRA_COMPARISON_HOLD_V2.md](integration/HIRA_COMPARISON_HOLD_V2.md)를 따른다.
보류는 `comparison.executed=false`, 결과 null이며 정상 비교 0건과 구분한다.

## 로컬 합성 사진 업로드 연결 (추가 계약)

기존 공통 결과 및 HIRA v1/v2, 사진 Mock 계약은 유지한다.
승인된 가상 검사 범위에서 별도 `/api/local-demo/photo-uploads/*`와
`UPLOADED_PHOTO_V1` 응답 버전을 추가한다. 이미지 검사·후보 snapshot·검토·비교 연결은
[PHOTO_UPLOAD_V1.md](integration/PHOTO_UPLOAD_V1.md)를 따른다.
실제 AI 인식/영구 저장/로그인/가족 권한/운영 공개를 제공하는 계약은 아니다.

## 개발용 계정·저장 추가 계약

`/api/dev-account`의 `DEV_ACCOUNT_V1` envelope로 로그인·세션·소유 가족·사진 결과 저장을
분리한다. 기존 공통 약 정보와 사진 Mock/업로드·HIRA 계약은 유지한다.
[DEV_ACCOUNT_STORAGE_V1.md](integration/DEV_ACCOUNT_STORAGE_V1.md)의 소유권·초안/확인/복용 구분을 따른다.
명시적 개발 설정에서만 사용하며 운영 인증·저장 계약으로 확정한 것은 아니다.

## 개발용 계정 HIRA 저장 추가 계약

기존 HIRA v2 결과를 변경하지 않고 `DEV_ACCOUNT_HIRA_V1` envelope에 담아
로그인 사용자 소유 가족의 HIRA 목록·보류·비교·별도 복용 확인을 보존한다.
사진 저장 계약은 유지한다. 입력·응답·DB v1→v2 추가 migration은
[ACCOUNT_HIRA_STORAGE_V1.md](integration/ACCOUNT_HIRA_STORAGE_V1.md)를 따른다.

## 개발용 저장 결과 삭제 추가 계약

저장 사진/HIRA의 기존 경로에 소유권 검사가 있는 DELETE를 추가한다.
선택 snapshot과 연결 복용 확인만 한 transaction에서 삭제하며 공통 약 정보 의미는 유지한다.
범위·공유 임시 후보·백업 복원 시 제한은 [DELETION_BACKUP_REVIEW.md](integration/DELETION_BACKUP_REVIEW.md)를 따른다.

## 계정 Gemini 추출 경로 추가

공통 추출/약 정보/비교 계약은 유지한다. 별도 보호된 photos/gemini-extract 경로와
DEV_ACCOUNT_V1의 extraction_source/공식 매칭 출처, 계정 결과의 extraction_sources로
Gemini 요청 경로와 Mock을 구분한다. 서버 활성화·설정·시도 한도가 없으면 실패하며 fallback하지 않는다.
[Gemini 준비·출처·실호출 승인 전제](integration/GEMINI_PHOTO_PREPARATION.md)를 따른다.

## 임시 관리자 식약처 진단 (별도 계약)

공통 약 정보/사진/HIRA 계약은 변경하지 않는다. 기본 비활성인 관리자 전용
ADMIN_MFDS_PROBE_V1과 영속 1회 실행 규칙은
[integration/RENDER_MFDS_ADMIN_PROBE.md](integration/RENDER_MFDS_ADMIN_PROBE.md)를 따른다.
실제 의약품 매칭 전환이나 운영 관리자 인증 완성을 뜻하지 않는다.

## 계정의 명시적 식약처 매칭 경로 (옵트인)

기본/생략 official_mode=LOCAL_MOCK은 유지한다. 계정 사진 JSON·HIRA form에만
MFDS_LIVE 선택을 추가하며 별도 서버 허용이 없으면 중단한다.
실제 HIRA 결과는 TASK_D_HIRA_MFDS_V1으로 구분한다. 공통 약 정보와 기존 공개 HIRA v2는 유지한다.
출처·전체 보류·요청 한도·저장 영향은 [MFDS_LIVE_MATCHING_V1.md](integration/MFDS_LIVE_MATCHING_V1.md)를 따른다.

실제 매칭 결과의 선택적 official_lookup(MFDS_LOOKUP_DIAGNOSTICS_V1)은
[HIRA_LOOKUP_FAILURE_REVIEW.md](integration/HIRA_LOOKUP_FAILURE_REVIEW.md)의 안전한 출처·오류 분류를 따른다.
구형 저장 결과의 필드 부재는 허용하며 원인을 추정해 채우지 않는다. 약 정보/비교 상태 의미는 유지한다.
