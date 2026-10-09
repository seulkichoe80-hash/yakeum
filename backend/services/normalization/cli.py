"""사용: python -m backend.services.normalization.cli 진료내역.xlsx [--real] [--out result.json] [-v]"""
import argparse
import json
import logging
import sys

from backend.services.mfds.mock_client import MockMfdsClient
from backend.services.mfds.real_client import RealMfdsClient
from backend.services.normalization.service import normalize_hira_file, summarize


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="HIRA Excel → NormalizationResult JSON")
    ap.add_argument("xlsx")
    ap.add_argument("--real", action="store_true", help="실제 식약처 API 사용 (환경변수 MFDS_API_KEY 필요)")
    ap.add_argument("--out", help="결과 JSON 저장 경로 (없으면 stdout)")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s", stream=sys.stderr)

    client = RealMfdsClient() if a.real else MockMfdsClient()
    results = normalize_hira_file(a.xlsx, client=client)
    text = json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        print(text)
    print(json.dumps(summarize(results), ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
