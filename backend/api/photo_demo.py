"""Explicit, stateless LOCAL_MOCK harness; not a team/public photo API.

Replays virtual A JSON through the common adapter; never reads uploaded images,
imports the live provider, calls MFDS, authenticates or persists data. Pending
policy cases withhold the whole comparison rather than invent absence results.
"""

from copy import deepcopy
from datetime import date
from decimal import Decimal
import json
import re
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from backend.services.extraction import ExtractionContext, adapt_gemini_response
from backend.services.mfds.mock_client import MockMfdsClient
from backend.services.mfds.models import OfficialIngredient, OfficialItem
from backend.services.normalization.repeat_report import find_repeat_groups
from backend.services.normalization.structured import normalize_structured_record
from backend.services.reconciliation.b_integration import reconcile_normalization_results
from backend.services.reconciliation.current_intake import build_current_intake_states

router = APIRouter(prefix="/api/local-demo/photos", tags=["LOCAL_MOCK only"])
Scenario = Literal["single", "multiple", "missing", "failed", "repeat", "unknown"]
Text = Annotated[str, Field(max_length=2000)]
NumberText = Annotated[str, Field(max_length=80)]


class LocalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DocumentInput(LocalModel):
    document_id: UUID
    record_date: date
    source_type: Literal["MEDICINE_BAG", "PRESCRIPTION", "SUPPLEMENT"]
    scenario: Scenario


class ExtractInput(DocumentInput):
    family_member_id: UUID


class IngredientDraft(LocalModel):
    name: Text
    strength: NumberText
    unit: Text
    originalIndex: int | None = None


class Draft(LocalModel):
    product: Text
    ingredients: list[IngredientDraft] = Field(max_length=32)
    dose: NumberText
    doseUnit: Text
    perDay: NumberText
    duration: NumberText
    directions: Text


class Review(LocalModel):
    index: int = Field(ge=0, le=31)
    confirmed: StrictBool
    draft: Draft


class Batch(DocumentInput):
    reviews: list[Review] = Field(max_length=32)


class ProcessInput(LocalModel):
    family_member_id: UUID
    previous: Batch
    current: Batch
    normalization_confirmed: StrictBool = False


def _fixture(scenario: Scenario) -> str:
    if scenario == "failed":
        return "intentionally invalid virtual provider response"
    def med(name, ingredient, strength="100"):
        return {"product_name_raw": name, "ingredients": [
            {"ingredient_name_raw": ingredient, "product_strength": strength,
             "product_strength_unit": "mg" if strength is not None else None}],
            "unit": "정", "dose_per_administration": "1", "administrations_per_day": "2",
            "duration_days": "7", "dosage_text_raw": "가상 원문: 하루 두 번 한 정", "confidence": "0.91"}
    first = med("가상알파정", "가상알파성분")
    meds = [first]
    if scenario == "multiple":
        second = med("가상오메가캡슐", "가상오메가성분", "0.50")
        second["ingredients"].append({"ingredient_name_raw": "가상보조성분", "product_strength": "20", "product_strength_unit": "mg"})
        meds.append(second)
    elif scenario == "missing":
        meds = [{**first, "product_name_raw": None}, med("가상알파정", "가상알파성분", None)]
    elif scenario == "repeat":
        meds.append(deepcopy(first))
    elif scenario == "unknown":
        meds = [med("가상알파정", "가상알파성분", None)]
    return json.dumps({"document_type": "약봉투", "medications": meds}, ensure_ascii=False)


def extract_virtual(family: str, doc: DocumentInput) -> list[dict[str, Any]]:
    raw = json.loads(_fixture(doc.scenario)) if doc.scenario != "failed" else None
    if raw is not None:
        raw["document_type"] = {"MEDICINE_BAG": "약봉투", "PRESCRIPTION": "처방전", "SUPPLEMENT": "건강기능식품"}[doc.source_type]
    return adapt_gemini_response(
        json.dumps(raw, ensure_ascii=False) if raw is not None else _fixture("failed"),
        ExtractionContext(family, str(doc.document_id), doc.record_date.isoformat()),
    )


@router.post("/extract")
def extract(request: ExtractInput):
    return {"mode": "LOCAL_MOCK", "persisted": False,
            "document_id": str(request.document_id),
            "results": extract_virtual(str(request.family_member_id), request)}


def _catalog():
    return MockMfdsClient(items=[
        OfficialItem("LOCAL_MOCK", "virtual-alpha", "가상알파정", [OfficialIngredient("가상알파성분", Decimal("100"), "mg")]),
        OfficialItem("LOCAL_MOCK", "virtual-omega", "가상오메가캡슐", [OfficialIngredient("가상오메가성분", Decimal("0.50"), "mg")]),
    ])


def _number(value: str):
    if value == "":
        return None
    if not re.fullmatch(r"(?:\d+(?:\.\d*)?|\.\d+)", value):
        raise ValueError("invalid decimal")
    return value


def _edited(original: dict, draft: Draft):
    r = deepcopy(original)
    if not draft.product.strip():
        raise ValueError("product required")
    r["product_name_raw"] = draft.product.strip()
    r["product_name_normalized"] = None
    r["mfds_product_id"] = None
    r["user_confirmed"] = False
    r["dosage_text_raw"] = draft.directions or None
    r["dose_per_administration"] = _number(draft.dose)
    r["unit"] = draft.doseUnit.strip() or None
    if (r["dose_per_administration"] is None) != (r["unit"] is None):
        raise ValueError("dose/unit pair required")
    r["administrations_per_day"] = _number(draft.perDay)
    r["duration_days"] = _number(draft.duration)
    r["ingredients"] = []
    for i in draft.ingredients:
        strength, unit = _number(i.strength), i.unit.strip() or None
        if (strength is None) != (unit is None) or not i.name.strip():
            raise ValueError("ingredient/strength/unit invalid")
        r["ingredients"].append({"ingredient_name_raw": i.name.strip(), "ingredient_name_normalized": None,
                                 "product_strength": strength, "product_strength_unit": unit,
                                 "official_ingredient_id": None})
    return r


def process_virtual(request: ProcessInput):
    family = str(request.family_member_id)
    reasons, snapshots = [], {"previous": [], "current": []}
    batches = {"previous": [], "current": []}
    originals = {"previous": [], "current": []}
    for side in ("previous", "current"):
        batch = getattr(request, side)
        source = extract_virtual(family, batch)
        originals[side] = deepcopy(source)
        indices = [review.index for review in batch.reviews]
        if len(indices) != len(set(indices)) or set(indices) != set(range(len(source))):
            reasons.append({"side": side, "message": "모든 후보를 중복 없이 검토해야 합니다."})
        reviews = {review.index: review for review in batch.reviews}
        for index, original in enumerate(source):
            review = reviews.get(index)
            if original["record"] is None or original["status"] == "FAILED":
                reasons.append({"side": side, "message": "원본 기록이 없거나 추출이 실패한 후보는 재추출/확인 보류가 필요합니다."})
                batches[side].append(normalize_structured_record(original, _catalog(), expected_family_member_id=family))
                continue
            if review is None or not review.confirmed:
                reasons.append({"side": side, "message": "추출 내용 대조가 완료되지 않은 후보가 있습니다."})
                continue
            try:
                edited = _edited(original["record"], review.draft)
            except ValueError:
                reasons.append({"side": side, "message": "후보 수정값의 제품명·수량·단위를 확인해 주세요."})
                continue
            snapshots[side].append(deepcopy(edited))
            result = normalize_structured_record({**original, "record": edited}, _catalog(), expected_family_member_id=family)
            batches[side].append(result)
            r = result["record"]
            if r is None or result["status"] in {"FAILED", "PARTIAL"}:
                reasons.append({"side": side, "message": "정규화 실패 또는 복수/부분 매칭은 비교 정책 확정 전 보류합니다."})
            elif not r["ingredients"] or any(
                not i["ingredient_name_normalized"] or i["product_strength"] is None or not i["product_strength_unit"]
                for i in r["ingredients"]
            ):
                reasons.append({"side": side, "message": "성분·함량·단위가 미확인입니다. 동일 함량으로 판정하지 않고 비교를 보류합니다."})
            # Strict demo gate avoids equating rule-normalized names with verified
            # identity. This does not change HIRA's existing UNMATCHED handling.
            elif result["status"] != "MATCHED":
                reasons.append({"side": side, "message": "제품 식별이 미확정이므로 사진 비교를 보류합니다."})
        if find_repeat_groups(batches[side]):
            reasons.append({"side": side, "message": "반복 기록의 대표 선택 정책이 미합의입니다. 기록을 삭제하지 않고 양쪽 비교를 보류합니다."})
    if request.previous.document_id == request.current.document_id:
        reasons.append({"side": "both", "message": "같은 문서를 이전/현재 양쪽에 중복 제출할 수 없습니다."})
    previous_by_product = {r["record"]["mfds_product_id"]: r["record"] for r in batches["previous"] if r["record"] is not None}
    for result in batches["current"]:
        current = result["record"]
        previous = previous_by_product.get(current["mfds_product_id"]) if current else None
        if previous and sorted(i["ingredient_name_normalized"] or "" for i in previous["ingredients"]) != sorted(i["ingredient_name_normalized"] or "" for i in current["ingredients"]):
            reasons.append({"side": "both", "message": "같은 제품의 성분 구성이 일치하지 않아 동일 함량으로 확정하지 않습니다."})
    base = {"mode": "LOCAL_MOCK", "persisted": False, "original_results": originals,
            "edited_records": snapshots, "normalization_results": batches,
            "pending_decisions": reasons, "reconciliation_result": None, "current_intake_states": []}
    if reasons:
        return {**base, "stage": "held"}
    if not request.normalization_confirmed:
        return {**base, "stage": "normalized"}
    # Only the explicit final user action confirms normalized snapshots. B never
    # sets this flag. Originals and preview snapshots remain unchanged.
    confirmed = deepcopy(batches)
    for side in confirmed:
        for result in confirmed[side]:
            result["record"]["user_confirmed"] = True
    integrated = reconcile_normalization_results(confirmed["previous"], confirmed["current"], family)
    return {**base, "stage": "compared", "normalization_results": confirmed,
            "reconciliation_result": integrated["reconciliation_result"],
            "current_intake_states": build_current_intake_states(integrated["reconciliation_result"])}


@router.post("/process")
def process(request: ProcessInput):
    return process_virtual(request)
