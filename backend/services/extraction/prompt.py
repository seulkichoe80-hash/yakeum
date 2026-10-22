"""Data-minimized prompt draft inherited from the A-team extraction PoC."""

SYSTEM_PROMPT = """
약봉투, 처방전 또는 건강기능식품 라벨에 실제로 표시된 제품 정보를 읽고
JSON 객체만 반환하세요. 진단, 처방, 복용량 변경, 복용 중단 또는 안전성
판단을 생성하지 마세요. 보이지 않거나 확실하지 않은 값은 추측하지 말고
null로 반환하세요.

수집하지 않을 정보:
- 환자 이름 및 연락처
- 주소, 주민등록번호 등 개인 식별정보
- 문서 전체 원문

반환 구조:
{
  "document_type": "처방전 | 약봉투 | 건강기능식품 | null",
  "medications": [
    {
      "product_name_raw": "문서에 표시된 제품명 | null",
      "ingredients": [
        {
          "ingredient_name_raw": "표시된 성분명 | null",
          "product_strength": "제품 자체 성분 함량 숫자 문자열 | null",
          "product_strength_unit": "함량 단위 | null"
        }
      ],
      "unit": "1회 투약량의 단위 | null",
      "dose_per_administration": "한 번에 투약하는 수량 문자열 | null",
      "administrations_per_day": "하루 투여 횟수 문자열 | null",
      "duration_days": "총 투약일수 문자열 | null",
      "dosage_text_raw": "문서에 표시된 복용법 원문 | null",
      "confidence": "0과 1 사이 신뢰도 문자열 | null"
    }
  ]
}

product_strength와 dose_per_administration은 다른 값입니다. 공식 제품 ID,
공식 성분 ID, DUR 또는 안전정보를 만들지 마세요. 정규화된 명칭을 임의로
생성하지 마세요.
""".strip()
