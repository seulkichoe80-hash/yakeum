import type { ReconciliationResult } from './types';

// Exact virtual fixture from docs/API_CONTRACT.md section 5.
export const contractMock: ReconciliationResult = {
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
};
