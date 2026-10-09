"""공식 데이터 매칭: CODE_EXACT → NAME_EXACT → NAME_FUZZY → NONE (먼저 성공하면 중단)."""
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import List, Optional

from backend.services.mfds.client import MfdsClient
from backend.services.mfds.models import OfficialItem
from backend.services.normalization.name_normalizer import normalize_name


@dataclass
class MatchOutcome:
    method: str  # CODE_EXACT | NAME_EXACT | NAME_FUZZY | NONE
    candidates: List[OfficialItem] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    lookup_failed: bool = False


def match(client: MfdsClient, drug_code: Optional[str], name: Optional[str], threshold: float) -> MatchOutcome:
    warns: List[str] = []
    failed = False

    if drug_code:
        hits = client.find_by_code(drug_code)
        warns += client.last_warnings
        failed = failed or client.last_failed
        if hits:
            return MatchOutcome("CODE_EXACT", hits, warns, failed)

    norm = normalize_name(name)
    if not norm:
        return MatchOutcome("NONE", [], warns, failed)

    pool = client.search_by_name(norm)  # 정규화한 이름으로 후보 조회, 판정은 아래에서 로컬로
    warns += client.last_warnings
    failed = failed or client.last_failed
    exact = [i for i in pool if normalize_name(i.name) == norm]
    if exact:
        return MatchOutcome("NAME_EXACT", exact, warns, failed)

    scored = [(SequenceMatcher(None, norm, normalize_name(i.name) or "").ratio(), i) for i in pool]
    fuzzy = [i for s, i in sorted(scored, key=lambda t: (-t[0], t[1].official_id)) if s >= threshold]
    if fuzzy:
        return MatchOutcome("NAME_FUZZY", fuzzy, warns, failed)
    return MatchOutcome("NONE", [], warns, failed)
