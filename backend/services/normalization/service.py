"""파서 결과 + 식약처 조회 결과를 합쳐 NormalizationResult 리스트를 만든다."""
import logging
from pathlib import Path
from typing import List, Optional

import yaml

from backend.services.hira.parser import parse_hira_excel
from backend.services.mfds.client import MfdsClient
from backend.services.mfds.mock_client import MockMfdsClient
from backend.services.normalization.matcher import match
from backend.services.normalization.models import (
    STATUS_FAILED,
    STATUS_MATCHED,
    STATUS_PARTIAL,
    STATUS_UNMATCHED,
    Ingredient,
    MatchInfo,
    NormalizationResult,
    ParsedRow,
    TextField,
)
from backend.services.normalization.name_normalizer import normalize_name

log = logging.getLogger(__name__)
DEFAULT_CONFIG = Path(__file__).parent / "config.yaml"


def load_config(path: Optional[Path] = None) -> dict:
    return yaml.safe_load(Path(path or DEFAULT_CONFIG).read_text(encoding="utf-8"))


def normalize_row(row: ParsedRow, client: MfdsClient, threshold: float) -> NormalizationResult:
    rec = row.record
    warnings = list(row.warnings)
    if row.errors:
        return NormalizationResult(STATUS_FAILED, rec, MatchInfo(), warnings, list(row.errors))

    try:
        out = match(client, rec.drug_code, rec.product_name.raw, threshold)
    except Exception as e:  # noqa: BLE001 - 조회 실패도 행 단위로 기록
        log.warning("MFDS lookup failed: %s", e)
        warnings.append(f"공식 데이터 조회 실패: {e}")
        return NormalizationResult(STATUS_UNMATCHED, rec, MatchInfo(), warnings, [])
    warnings += out.warnings

    if not out.candidates:
        if out.lookup_failed:
            warnings.append("공식 데이터 조회 실패로 매칭하지 못함 (재시도 필요, 원본 값 보존)")
        else:
            warnings.append("공식 데이터에서 찾지 못함 (원본 값 보존)")
        return NormalizationResult(STATUS_UNMATCHED, rec, MatchInfo(), warnings, [])

    if len(out.candidates) > 1:
        ids = ", ".join(c.official_id for c in out.candidates)
        warnings.append(f"후보 {len(out.candidates)}건 ({out.method}): {ids}")
        return NormalizationResult(
            STATUS_PARTIAL, rec, MatchInfo(None, None, out.method), warnings, []
        )

    item = out.candidates[0]
    info = MatchInfo(item.source, item.official_id, out.method)
    rec.official_name = item.name  # raw 는 덮어쓰지 않고 별도 필드로 보관
    status = STATUS_MATCHED
    if not rec.ingredients:
        if item.ingredients:
            rec.ingredients = [
                Ingredient(TextField(i.name, normalize_name(i.name)), i.amount, i.unit, None, "MFDS", i.ingredient_id)
                for i in item.ingredients
            ]
        else:
            status = STATUS_PARTIAL
            warnings.append("공식 데이터에 성분 정보가 없어 일부만 확인됨")
    return NormalizationResult(status, rec, info, warnings, [])


def _threshold(config: Optional[dict]) -> float:
    t = float((config or load_config()).get("fuzzy_threshold", 0.9))
    if not 0.0 < t <= 1.0:
        raise ValueError(f"fuzzy_threshold 는 (0, 1] 범위여야 함: {t}")
    return t


def summarize(results: List[NormalizationResult]) -> dict:
    counts = {s: 0 for s in (STATUS_MATCHED, STATUS_PARTIAL, STATUS_UNMATCHED, STATUS_FAILED)}
    for r in results:
        counts[r.status] += 1
    return {"total": len(results), **counts}


def normalize_rows(rows: List[ParsedRow], client: Optional[MfdsClient] = None, config: Optional[dict] = None):
    client = client or MockMfdsClient()
    threshold = _threshold(config)
    results = []
    for r in rows:
        try:
            results.append(normalize_row(r, client, threshold))
        except Exception as e:  # noqa: BLE001 - 한 행의 예기치 못한 오류가 전체를 막지 않게
            log.exception("row normalization crashed")
            results.append(NormalizationResult(STATUS_FAILED, r.record, MatchInfo(), list(r.warnings), [f"정규화 중 예외: {e}"]))
    log.info("normalized: %s", summarize(results))
    return results


def normalize_hira_file(path, client: Optional[MfdsClient] = None, config: Optional[dict] = None, mapping_path=None):
    return normalize_rows(parse_hira_excel(path, mapping_path), client, config)
