"""사용:
  내부 형식   : python -m backend.services.normalization.cli 투약이력.xlsx [--real] [--out result.json] [-v]
  공통 형식   : python -m backend.services.normalization.cli 투약이력.xlsx --common --family-member-id <UUID> [--out result.json]
(공통 형식 = docs/DATA_SCHEMA.md MedicationRecord + docs/API_CONTRACT.md NormalizationResult, D 팀 전달용)
"""
import argparse
import json
import logging
import sys

from backend.services.mfds.mock_client import MockMfdsClient
from backend.services.mfds.real_client import RealMfdsClient
from backend.services.normalization.adapter import to_common_results, validate_common_result
from backend.services.normalization.service import normalize_hira_file, summarize


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="HIRA Excel → NormalizationResult JSON")
    ap.add_argument("xlsx")
    ap.add_argument("--real", action="store_true", help="실제 식약처 API 사용 (환경변수 MFDS_API_KEY 필요)")
    ap.add_argument("--common", action="store_true", help="공통 규격(MedicationRecord/NormalizationResult)으로 출력")
    ap.add_argument("--family-member-id", help="--common 에 필요한 가족 구성원 UUID (B 는 생성하지 않음)")
    ap.add_argument("--out", help="결과 JSON 저장 경로 (없으면 stdout)")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    if a.common and not a.family_member_id:
        ap.error("--common 은 --family-member-id 가 필요합니다 (가족 ID 를 추측하지 않음)")
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s", stream=sys.stderr)

    client = RealMfdsClient() if a.real else MockMfdsClient()
    results = normalize_hira_file(a.xlsx, client=client)
    if a.common:
        try:
            payload = to_common_results(results, a.family_member_id)
        except ValueError as e:
            ap.error(str(e))
        for i, r in enumerate(payload):
            for problem in validate_common_result(r):
                print(f"[계약 점검] {i + 1}번째 결과: {problem}", file=sys.stderr)
    else:
        payload = [r.to_dict() for r in results]
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        print(text)
    print(json.dumps(summarize(results), ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
