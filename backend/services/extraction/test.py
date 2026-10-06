# test.py
from extraction import extract_medicine_info

def test_extraction(image_path: str):
    print("=" * 50)
    print("약 정보 추출 테스트 시작!")
    print("=" * 50)

    result = extract_medicine_info(image_path)

    print(f"\n📄 문서 종류: {result.document_type.value}")
    print(f"👤 환자 이름: {result.patient_name}")
    print(f"🏥 병원/약국: {result.hospital_name}")
    print(f"📅 처방 날짜: {result.prescription_date}")
    print(f"🔍 전체 신뢰도: {result.overall_confidence}")

    print(f"\n💊 약 목록 ({len(result.medications)}개):")
    for i, med in enumerate(result.medications, 1):
        print(f"\n  [{i}] {med.name}")
        print(f"      용량: {med.dosage}")
        print(f"      횟수: {med.frequency}")
        print(f"      기간: {med.duration}")
        print(f"      시점: {med.timing.value}")
        print(f"      특이사항: {med.instructions}")
        print(f"      신뢰도: {med.confidence}")

    print("\n" + "=" * 50)
    print("테스트 완료!")
    print("=" * 50)

    return result


if __name__ == "__main__":
    IMAGE_PATH = "test_image.jpg"  # ← 이미지 파일명
    test_extraction(IMAGE_PATH)