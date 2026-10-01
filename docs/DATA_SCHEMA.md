# MedicationRecord Schema v1 Draft

이 문서는 약이음 4명 공동개발을 위한 데이터 계약 초안이다. 실제 DB Schema, ORM 모델 또는 API 계약을 확정하지 않으며, 구현 전에 팀 합의를 거쳐야 한다.

## 입력 처리 원칙

1. 심평원 「내가 먹는 약! 한눈에」 Excel은 이미 구조화된 데이터이므로 AI가 아닌 deterministic parser로 처리한다.
2. 약봉투, 처방전, 건강기능식품 등 비정형 자료만 Multimodal AI를 사용해 구조화한다.
3. `raw` 값은 원본 보존용이다. 정규화 결과로 덮어쓰지 않는다.
4. 정규화 또는 공식 데이터 매칭에 실패해도 확인 가능한 원본값은 유지한다.
5. 실제 개인정보나 건강정보가 포함된 자료는 Repository에 저장하거나 commit하지 않는다.

## 공통 표기

- 필수 여부의 `필수`는 모든 저장 레코드에 필요함을 의미한다.
- `조건부`는 특정 출처 또는 선행 필드가 있을 때 필요함을 의미한다.
- `선택`은 원본에 없거나 아직 확인되지 않을 수 있음을 의미한다.
- 날짜는 ISO 8601의 `YYYY-MM-DD` 형식을 사용한다.
- Decimal 값은 `float`로 처리하지 않는다. DB에서는 `DECIMAL`/`NUMERIC`, API에서는 정밀도를 보존할 수 있는 문자열 표현을 우선 검토한다.
- `null`은 미확인, 원본에 없음 또는 아직 공식 데이터에 매칭되지 않았음을 의미한다. `0`, `false`, 빈 문자열과 구분한다.

## MedicationRecord

| 필드 | 논리 타입 | 필수 여부 | 정의 |
| --- | --- | --- | --- |
| `record_id` | UUID | 필수 | 시스템이 생성하는 MedicationRecord 식별자 |
| `family_member_id` | UUID | 필수 | 복용정보가 속한 가족 구성원 식별자 |
| `source_type` | Enum | 필수 | 입력 자료 유형 |
| `source_record_id` | String | 필수 | 원본 내 항목의 재식별 및 재업로드 중복 확인에 사용하는 식별자 |
| `record_date` | Date | 필수 | Timeline 및 Reconciliation에서 사용하는 대표 기준일 |
| `dispensing_date` | Date | 조건부 | 실제 조제일. `HIRA`에서는 필수 |
| `prescribing_institution` | String | 선택 | 처방기관명 |
| `dispensing_institution` | String | 선택 | 조제기관명 |
| `product_name_raw` | String | 필수 | 원본에서 확인한 제품명 |
| `product_name_normalized` | String | 선택 | 정규화하거나 공식 데이터에 매칭한 제품명 |
| `drug_code` | String | 선택 | 원본 약품코드. 선행 0과 원래 표현을 보존하기 위해 숫자 타입을 사용하지 않음 |
| `drug_category` | String | 선택 | 원본 약효분류 또는 공식 분류 |
| `unit` | String | 선택 | 1회 투약량에 적용되는 단위. 예: `정`, `캡슐`, `mL` |
| `dose_per_administration` | Decimal | 선택 | 사용자가 한 번에 투약하는 수량. 예: `1`과 `정` |
| `administrations_per_day` | Decimal | 선택 | 하루 투여 횟수 |
| `duration_days` | Decimal | 선택 | 총 투약일수 |
| `dosage_text_raw` | String | 선택 | 원본 복용법 문구. 예: `아침 식후 1정` |
| `mfds_product_id` | String | 선택 | 식약처 공식 제품 식별자 매칭 결과 |
| `ingredients` | Ingredient[] | 필수 | 제품을 구성하는 성분 또는 기능성 원료 목록. 빈 배열 허용 여부는 TODO |
| `confidence` | Decimal (0–1) | 조건부 | AI를 사용한 비정형 입력의 record-level 신뢰도 |
| `user_confirmed` | Boolean | 필수 | 사용자가 추출·정규화 결과를 직접 확인하고 확정했는지 여부 |

### `source_type`

- `HIRA`: 심평원 투약이력 Excel
- `PRESCRIPTION`: 처방전
- `MEDICINE_BAG`: 약봉투
- `SUPPLEMENT`: 건강기능식품

## Ingredient

복합제와 복수 기능성 원료를 표현하기 위해 `MedicationRecord.ingredients[]`를 사용한다.

| 필드 | 논리 타입 | 필수 여부 | 정의 |
| --- | --- | --- | --- |
| `ingredient_name_raw` | String | 선택 | 원본에서 확인한 성분명 또는 기능성 원료명 |
| `ingredient_name_normalized` | String | 선택 | 정규화한 성분명 또는 기능성 원료명 |
| `product_strength` | Decimal | 선택 | 제품 자체에 포함된 해당 성분의 함량. 예: `200` |
| `product_strength_unit` | String | 조건부 | `product_strength`의 단위. 예: `mg`, `mcg`, `mg/mL` |
| `official_ingredient_id` | String | 선택 | 공식 데이터에 매칭한 성분 식별자 |

`product_strength`와 `dose_per_administration`은 서로 다른 개념이며 별도로 저장하고 비교한다.

- `product_strength`: 제품 자체의 성분 함량. 예: `200 mg`
- `dose_per_administration`: 사용자가 한 번에 투약하는 수량. 예: `1 정`

건강기능식품은 한 제품에 복수의 기능성 원료가 있을 수 있으므로 단일 성분 필드 대신 `ingredients[]`를 사용한다.

## 데이터 출처 원칙

| 출처 | 처리 방식 | 대표 데이터 |
| --- | --- | --- |
| 심평원 Excel | deterministic parser | 조제일자, 기관, 제품명, 약효분류, 성분명, 약품코드, 단위, 투약량, 투여횟수, 투약일수, 안전정보 |
| 약봉투·처방전·건강기능식품 | Multimodal AI 추출 후 사용자 확인 | 제품명, 성분, 함량, 복용법 및 문서에 표시된 정보 |
| 식약처 공식 데이터 | 매칭 및 정규화 보완 | 공식 제품·성분 식별자, 정규화 명칭, 공식 근거 |
| 시스템 | 생성 및 관리 | `record_id`, `source_type`, `source_record_id` 등 |
| 사용자 | 확인 및 수정 | AI 결과 수정, 정규화 결과 확인, `user_confirmed` |

AI 추출 결과가 불확실한 경우 자동 확정하지 않으며 사용자가 수정·확정할 수 있어야 한다. `confidence`는 v1 Draft에서 record-level로 유지한다.

## 안전정보 및 Evidence

안전성 서한, DUR 등 긴 원문을 `MedicationRecord`마다 직접 복제하는 구조로 확정하지 않는다. AI가 안전정보를 임의로 생성하거나 최종 판단해서는 안 된다.

향후 공식 근거 ID, 출처, 조회 시점 및 적용 대상을 연결하는 별도 `Evidence` 구조를 검토한다.

## Reconciliation v1 상태

Reconciliation 상태는 현재 `AGENTS.md`와 동일하게 유지하며 새로운 상태값을 추가하지 않는다.

- 동일 성분 + 동일 함량 지속 → `MAINTAINED`
- 이전 기록 없이 현재 자료에 존재 → `NEW`
- 동일 성분 + 함량 변화 → `DOSE_CHANGED`
- 과거 기록에 존재하지만 최신 자료에서 확인되지 않음 → `NEEDS_CONFIRMATION`

최신 자료에서 확인되지 않는다는 이유만으로 복용 중단으로 판단하지 않는다.

Reconciliation에서는 `product_strength`와 `dose_per_administration`을 별도로 취급한다. 두 값의 변화는 현재 `DOSE_CHANGED` 범위에서 다루되, 향후 제품 함량 변화와 실제 투약량 변화의 세부 변화 유형을 분리해야 한다.

## TODO: 팀 합의가 필요한 사항

- 출처별 `record_date` 결정 규칙
- `source_record_id` 생성 규칙
- `drug_code_type` 필요 여부
- Decimal precision
- 공식 데이터 매칭 상태 표현 방식
- 사용자 수정 이력 보존 방식
- 공식 근거를 연결할 `Evidence` 구조
- 건강기능식품 공식 제품 ID 체계
- 재업로드 중복 처리 정책
- product strength 변화와 dosage 변화의 세부 분류
- AI 검증 결과에 따른 field-level confidence 전환 여부
- `ingredients` 빈 배열 허용 여부와 최소 유효 조건

이 Schema는 **MedicationRecord Schema v1 Draft**이며 실제 DB Schema가 아니다. 4명의 담당자가 함께 검토하고 합의한 후 확정한다.
