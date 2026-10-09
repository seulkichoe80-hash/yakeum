"""실제 공공데이터포털 식약처 API 구현체.

- API 키는 환경변수 MFDS_API_KEY 로만 읽는다 (코드/로그/커밋에 남기지 않는다).
- 실패/타임아웃 시 지수 백오프로 재시도하고, 끝내 실패하면 예외 대신 warnings 에 기록한다.
- 성공한 조회는 메모리 캐시에 저장한다 (실패는 캐시하지 않는다).
- 응답 필드 매핑은 api_config.yaml 로 분리했다 (실제 응답 미검증 → 팀장/실데이터로 확인 필요).
"""
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml

from backend.services.mfds.client import MfdsClient
from backend.services.mfds.models import OfficialIngredient, OfficialItem

log = logging.getLogger(__name__)
DEFAULT_CONFIG = Path(__file__).parent / "api_config.yaml"

Transport = Callable[[str, Dict[str, Any], float], Any]


class MfdsApiError(Exception):
    """재시도해도 소용없는 API 수준 오류(인증 실패 등)."""


def default_transport(url: str, params: Dict[str, Any], timeout: float) -> Any:
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{url}?{query}", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - https 고정 URL
        return json.loads(resp.read().decode("utf-8"))


def _dig(obj: Any, path: List[str]) -> Any:
    for p in path:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(p)
    return obj


def _items(payload: Any, path: List[str]) -> List[Dict[str, Any]]:
    node = _dig(payload, path)
    if not node:
        return []
    if isinstance(node, dict):
        node = node.get("item", node)
    if isinstance(node, dict):
        node = [node]
    out = []
    for it in node if isinstance(node, list) else []:
        if isinstance(it, dict):
            out.append(it.get("item", it) if isinstance(it.get("item"), dict) else it)
    return out


def _split_code_prefix(s: str) -> Tuple[Optional[str], str]:
    """"[M040702]아세트아미노펜" → ("M040702", "아세트아미노펜"). 접두 코드가 없으면 (None, 이름)."""
    s = s.strip()
    if s.startswith("[") and "]" in s:
        code, rest = s[1:].split("]", 1)
        return (code.strip() or None), rest.strip()
    return None, s


def parse_item(raw: Dict[str, Any], cfg: Dict[str, Any]) -> Optional[OfficialItem]:
    f = cfg["fields"]
    oid, name = raw.get(f["id"]), raw.get(f["name"])
    if oid in (None, "") or not name:
        return None
    ings: List[OfficialIngredient] = []
    ing_field = f.get("ingredients")
    if ing_field and raw.get(ing_field):
        for part in str(raw[ing_field]).split(cfg.get("ingredient_separator", "|")):
            ing_id, n = _split_code_prefix(part)
            if n:
                ings.append(OfficialIngredient(name=n, ingredient_id=ing_id))  # 함량은 응답에 없다고 가정 → None
    form = raw.get(f["form"]) if f.get("form") else None
    ins_field = f.get("insurance_code")
    ins = raw.get(ins_field) if ins_field else None
    ins = str(ins).strip() if ins not in (None, "") else None
    return OfficialItem(cfg["source"], str(oid).strip(), str(name).strip(), ings, form or None, ins)


class RealMfdsClient(MfdsClient):
    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 5.0,
        retries: int = 3,
        backoff: float = 0.5,
        transport: Optional[Transport] = None,
        sleep: Callable[[float], None] = time.sleep,
        config_path: Optional[Path] = None,
    ):
        self.api_key = api_key if api_key is not None else os.environ.get("MFDS_API_KEY", "")
        self.timeout, self.retries, self.backoff = timeout, retries, backoff
        self._transport = transport or default_transport
        self._sleep = sleep
        self.config = yaml.safe_load(Path(config_path or DEFAULT_CONFIG).read_text(encoding="utf-8"))
        self._cache: Dict[Tuple[str, str, str], List[OfficialItem]] = {}
        self.last_warnings: List[str] = []
        self.last_failed = False
        self.calls = 0  # 실제 네트워크 호출 횟수(캐시 검증용)

    # -- public ---------------------------------------------------------
    def find_by_code(self, code: str) -> List[OfficialItem]:
        """HIRA 약품코드(보험코드)로 조회한다.

        품목기준코드(ITEM_SEQ 등 official_id)는 보험코드와 다른 체계이므로 비교하지 않는다.
        api_config.yaml 에 insurance_code_param / fields.insurance_code 가 확인·설정된 소스만 조회하고,
        설정이 없으면 코드 조회를 건너뛴다(이름 매칭으로 진행). 실제 명세 확인 전까지 기본값은 건너뜀.
        """
        self._reset()
        out: List[OfficialItem] = []
        for key, cfg in self.config["sources"].items():
            param = cfg.get("insurance_code_param")
            if not param or not cfg["fields"].get("insurance_code"):
                continue
            items = self._query(key, cfg, param, code)
            out += [i for i in items if i.insurance_code == code]  # 문자열 정확 일치
        return out

    def search_by_name(self, name: str, limit: int = 50) -> List[OfficialItem]:
        self._reset()
        out: List[OfficialItem] = []
        for key, cfg in self.config["sources"].items():
            out += self._query(key, cfg, cfg["name_param"], name)
        return out[:limit]

    # -- internal -------------------------------------------------------
    def _reset(self) -> None:
        self.last_warnings, self.last_failed = [], False

    def _fail(self, key: str, msg: str) -> None:
        self.last_failed = True
        self.last_warnings.append(f"공식 데이터 조회 실패({key}): {msg}")
        log.warning("MFDS lookup failed (%s): %s", key, msg)

    def _query(self, key: str, cfg: Dict[str, Any], param: str, value: str) -> List[OfficialItem]:
        ck = (key, param, value)
        if ck in self._cache:
            return self._cache[ck]
        if not self.api_key:
            self._fail(key, "MFDS_API_KEY 환경변수가 설정되지 않음")
            return []
        params = {self.config["key_param"]: self.api_key, **cfg.get("extra_params", {}), param: value}
        payload = self._call_with_retry(key, cfg["url"], params)
        if payload is None:
            return []
        items = [i for i in (parse_item(r, cfg) for r in _items(payload, cfg["items_path"])) if i]
        self._cache[ck] = items
        return items

    def _call_with_retry(self, key: str, url: str, params: Dict[str, Any]) -> Any:
        last = "알 수 없는 오류"
        for attempt in range(self.retries + 1):
            self.calls += 1
            try:
                payload = self._transport(url, params, self.timeout)
                self._check_header(payload)
                return payload
            except MfdsApiError as e:
                self._fail(key, str(e))
                return None
            except urllib.error.HTTPError as e:
                last = f"HTTP {e.code}"
                if e.code < 500 and e.code != 429:  # 4xx 는 재시도해도 같다
                    break
            except Exception as e:  # noqa: BLE001 - 타임아웃/네트워크/JSON 오류 모두 재시도 대상
                last = f"{type(e).__name__}: {e}"
            if attempt < self.retries:
                log.info("MFDS retry %d/%d (%s): %s", attempt + 1, self.retries, key, last)
                self._sleep(self.backoff * (2**attempt))
        self._fail(key, f"{last} (재시도 {self.retries}회 후 포기)")
        return None

    def _check_header(self, payload: Any) -> None:
        header = _dig(payload, ["header"]) or _dig(payload, ["response", "header"])
        if not isinstance(header, dict):
            return
        code = str(header.get("resultCode", "00"))
        if code not in self.config.get("success_codes", ["00"]):
            raise MfdsApiError(f"API 오류 resultCode={code} {header.get('resultMsg', '')}".strip())
