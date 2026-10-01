# 공통 데이터 Schema 초안

## MedicationRecord (Draft)

아래 항목은 복용정보를 표현하기 위한 초기 필드 목록이며, 타입·필수 여부·제약조건·관계는 아직 확정하지 않는다.

| 필드 | 설명 상태 |
| --- | --- |
| `record_id` | Draft |
| `family_member_id` | Draft |
| `source_type` | Draft |
| `record_date` | Draft |
| `product_name_raw` | Draft |
| `product_name_normalized` | Draft |
| `ingredient_name` | Draft |
| `strength` | Draft |
| `strength_unit` | Draft |
| `dosage_text` | Draft |
| `mfds_product_id` | Draft |
| `confidence` | Draft |
| `user_confirmed` | Draft |

### `source_type` 후보

- `HIRA`
- `PRESCRIPTION`
- `MEDICINE_BAG`
- `SUPPLEMENT`

이 Schema는 현재 **Draft**이며 실제 DB Schema가 아니다. 4명의 담당자가 함께 검토하고 합의한 후 확정한다.
