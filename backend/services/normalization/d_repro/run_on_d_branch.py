"""D 코드가 있는 체크아웃에서 결함 재현 사례를 실행해 결과를 표로 출력한다 (읽기 전용, 파일 변경 없음).

사용 (D 통합 브랜치를 체크아웃한 저장소 루트에서):
    python backend/services/normalization/d_repro/run_on_d_branch.py

B 브랜치(feature/data-backend)에는 D 코드가 없어 import 에 실패하며, 이 경우 안내만 출력한다.
D 코드·공통 계약은 수정하지 않는다.
"""
import json
import sys
from pathlib import Path

CASES = Path(__file__).parent / "cases.json"


def main() -> int:
    try:
        from backend.services.reconciliation import reconcile_normalization_results
    except ImportError:
        print("D 의 reconcile_normalization_results 를 찾을 수 없습니다. D 통합 브랜치에서 실행하세요.")
        return 1
    data = json.loads(CASES.read_text(encoding="utf-8"))
    family = data["family_member_id"]
    for case in data["cases"]:
        out = reconcile_normalization_results(case["previous"], case["current"], family, generated_at="2026-10-18T00:00:00Z")
        print(f'\n[{case["id"]}] {case["title"]}')
        print(f'  기대(설계 의도): {case["expect_by_design"]}')
        for it in out["reconciliation_result"]["items"]:
            rec = it["current_record"] or it["previous_record"]
            print(f'  -> {it["status"]:<19} {it["reason_code"]:<32} {rec["product_name_raw"]} ({rec["dispensing_date"]})')
    return 0


if __name__ == "__main__":
    sys.exit(main())
