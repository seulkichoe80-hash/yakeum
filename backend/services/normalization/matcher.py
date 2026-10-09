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


def match(client: MfdsClient, drug_code: Optional[str], name: Optional[str], threshold: float) -> MatchOutcome:
    warns: List[str] = []

    if drug_code:
        hits = client.find_by_code(drug_code)
        warns += client.last_warnings
        if hits:
            return MatchOutcome("CODE_EXACT", hits, warns)

    norm = normalize_name(name)
    if not norm:
        return MatchOutcome("NONE", [], warns)

    pool = client.search_by_name(name or "")
    warns += client.last_warnings
    exact = [i for i in pool if normalize_name(i.name) == norm]
    if exact:
        return MatchOutcome("NAME_EXACT", exact, warns)

    scored = [(SequenceMatcher(None, norm, normalize_name(i.name) or "").ratio(), i) for i in pool]
    fuzzy = [i for s, i in sorted(scored, key=lambda t: (-t[0], t[1].official_id)) if s >= threshold]
    if fuzzy:
        return MatchOutcome("NAME_FUZZY", fuzzy, warns)
    return MatchOutcome("NONE", [], warns)
