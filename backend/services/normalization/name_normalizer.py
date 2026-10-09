"""제품명 정규화: 공백·괄호·제형·함량 표기를 제거한다 (결정적, 규칙 기반)."""
import re
import unicodedata
from typing import Optional

_BRACKETS = re.compile(r"[\(\[\{（][^\)\]\}）]*[\)\]\}）]")
_STRENGTH = re.compile(
    r"\d[\d,]*(?:\.\d+)?\s*(?:mg|g|mcg|μg|㎍|㎎|㎖|ml|iu|%)", re.IGNORECASE
)
_FORMS = (
    "서방정", "장용정", "필름코팅정", "연질캡슐", "경질캡슐", "캡슐", "시럽", "현탁액",
    "정제", "정", "산", "과립", "액", "주사", "크림", "연고", "패치",
)
_FORMS_RE = re.compile("(?:" + "|".join(_FORMS) + r")$")


def normalize_name(name: Optional[str]) -> Optional[str]:
    if name is None:
        return None
    s = unicodedata.normalize("NFKC", str(name))
    s = _BRACKETS.sub("", s)
    s = _STRENGTH.sub("", s)
    s = re.sub(r"\s+", "", s).lower()
    s = _FORMS_RE.sub("", s)
    s = re.sub(r"[^0-9a-z가-힣]", "", s)
    return s or None
