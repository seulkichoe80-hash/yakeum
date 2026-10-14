"""반복 조제 기록 진단 (읽기 전용).

B→D 통합 실험에서 한 시점 안에 같은 약이 여러 줄이면 D 가 동률 후보로 보고 추측하지 않아,
이어지는 약이 NEEDS_CONFIRMATION + NEW 로 갈라지는 것이 확인되었다. 팀장 결정에 따라 B 는 반복행을
삭제·축약하지 않는다. 이 모듈은 기록을 바꾸지 않고, 어떤 약이 몇 번 반복되는지만 알려 준다
(통합 계층이 사용자에게 알리거나 D 와 대표 기록 선택 방식을 정할 때 쓰는 진단 정보).

묶는 기준은 D 엔진의 식별 우선순위와 같은 방향(mfds_product_id → drug_code → 정규화 제품명+성분)이며,
의료적 판단이나 동일 약 확정이 아니라 "같은 키를 가진 기록 목록"만 만든다.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


def _identity_key(record: Mapping[str, Any]) -> Optional[Tuple[str, str]]:
    def text(v: Any) -> Optional[str]:
        return v.strip().casefold() if isinstance(v, str) and v.strip() else None

    mfds = text(record.get("mfds_product_id"))
    if mfds:
        return ("mfds_product_id", mfds)
    code = text(record.get("drug_code"))
    if code:
        return ("drug_code", code)
    name = text(record.get("product_name_normalized"))
    if name:
        names = []
        for ing in record.get("ingredients") or []:
            n = text(ing.get("ingredient_name_normalized")) if isinstance(ing, Mapping) else None
            if not n:
                return None  # 성분명이 비면 이름만으로 같은 약이라고 묶지 않는다
            names.append(n)
        if names:
            return ("name+ingredients", name + "|" + ",".join(sorted(names)))
    return None


def find_repeat_groups(common_results: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """같은 식별 키를 가진 기록이 2건 이상인 그룹 목록. 입력은 변경하지 않는다.

    FAILED(record: null) 는 제외한다. 반환 항목:
    {"key_type", "key", "count", "source_record_ids", "dispensing_dates"}
    """
    groups: "OrderedDict[Tuple[str, str], List[Mapping[str, Any]]]" = OrderedDict()
    for r in common_results:
        rec = r.get("record") if isinstance(r, Mapping) else None
        if not isinstance(rec, Mapping):
            continue
        key = _identity_key(rec)
        if key is not None:
            groups.setdefault(key, []).append(rec)
    out = []
    for (key_type, key), recs in groups.items():
        if len(recs) > 1:
            out.append({
                "key_type": key_type,
                "key": key,
                "count": len(recs),
                "source_record_ids": [x.get("source_record_id") for x in recs],
                "dispensing_dates": [x.get("dispensing_date") for x in recs],
            })
    return out
