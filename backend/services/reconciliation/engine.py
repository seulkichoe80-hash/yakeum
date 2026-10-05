"""Deterministic MedicationRecord reconciliation PoC.

This module compares already structured MedicationRecord dictionaries. It does
not make medical decisions and deliberately avoids guessing when identity or
comparable values are missing.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping, Sequence

MedicationRecord = Mapping[str, Any]

MAINTAINED = "MAINTAINED"
NEW = "NEW"
DOSE_CHANGED = "DOSE_CHANGED"
NEEDS_CONFIRMATION = "NEEDS_CONFIRMATION"

SAME_INGREDIENT_SAME_STRENGTH = "SAME_INGREDIENT_SAME_STRENGTH"
NEW_RECORD = "NEW_RECORD"
STRENGTH_OR_DOSAGE_CHANGED = "STRENGTH_OR_DOSAGE_CHANGED"
NOT_FOUND_IN_LATEST_SOURCE = "NOT_FOUND_IN_LATEST_SOURCE"


def reconcile_records(
    previous_records: Sequence[MedicationRecord],
    current_records: Sequence[MedicationRecord],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Return a ReconciliationResult for one family member.

    Records are paired by deterministic product identity. An unmatched current
    record is NEW. An unmatched previous record is NEEDS_CONFIRMATION; absence
    never means that medication was stopped.
    """

    family_member_id = _single_family_member_id(previous_records, current_records)
    unmatched_current = set(range(len(current_records)))
    items: list[dict[str, Any]] = []

    for previous in previous_records:
        current_index = _find_unique_best_match(
            previous, current_records, unmatched_current
        )
        if current_index is None:
            items.append(
                _result_item(
                    NEEDS_CONFIRMATION,
                    previous,
                    None,
                    NOT_FOUND_IN_LATEST_SOURCE,
                )
            )
            continue

        unmatched_current.remove(current_index)
        current = current_records[current_index]
        if _has_comparable_dose_change(previous, current):
            items.append(
                _result_item(
                    DOSE_CHANGED,
                    previous,
                    current,
                    STRENGTH_OR_DOSAGE_CHANGED,
                )
            )
        else:
            items.append(
                _result_item(
                    MAINTAINED,
                    previous,
                    current,
                    SAME_INGREDIENT_SAME_STRENGTH,
                )
            )

    for current_index, current in enumerate(current_records):
        if current_index in unmatched_current:
            items.append(_result_item(NEW, None, current, NEW_RECORD))

    return {
        "family_member_id": family_member_id,
        "generated_at": generated_at or _utc_now(),
        "items": items,
    }


def _single_family_member_id(
    previous_records: Sequence[MedicationRecord],
    current_records: Sequence[MedicationRecord],
) -> str:
    family_ids = {
        record.get("family_member_id")
        for record in (*previous_records, *current_records)
    }
    if not family_ids or None in family_ids or "" in family_ids:
        raise ValueError("Every MedicationRecord must have a family_member_id")
    if len(family_ids) != 1:
        raise ValueError("ReconciliationResult must contain exactly one family member")
    return str(next(iter(family_ids)))


def _find_unique_best_match(
    previous: MedicationRecord,
    current_records: Sequence[MedicationRecord],
    available_indices: Iterable[int],
) -> int | None:
    ranked_candidates: list[tuple[int, int]] = []
    for index in sorted(available_indices):
        rank = _identity_rank(previous, current_records[index])
        if rank is not None:
            ranked_candidates.append((rank, index))

    if not ranked_candidates:
        return None

    best_rank = min(rank for rank, _ in ranked_candidates)
    best_indices = [index for rank, index in ranked_candidates if rank == best_rank]

    # Multiple equally strong candidates are ambiguous. Do not guess a match.
    if len(best_indices) != 1:
        return None
    return best_indices[0]


def _identity_rank(left: MedicationRecord, right: MedicationRecord) -> int | None:
    """Return the product identity priority, or None when not safely matched."""

    left_mfds = _text(left.get("mfds_product_id"))
    right_mfds = _text(right.get("mfds_product_id"))
    if left_mfds and right_mfds:
        return 1 if left_mfds == right_mfds else None

    left_drug_code = _text(left.get("drug_code"))
    right_drug_code = _text(right.get("drug_code"))
    if left_drug_code and right_drug_code:
        return 2 if left_drug_code == right_drug_code else None

    left_product = _text(left.get("product_name_normalized"))
    right_product = _text(right.get("product_name_normalized"))
    left_ingredients = _normalized_ingredient_names(left)
    right_ingredients = _normalized_ingredient_names(right)
    if (
        left_product
        and right_product
        and left_product == right_product
        and left_ingredients
        and left_ingredients == right_ingredients
    ):
        return 3

    # Ingredient equality alone is only a candidate signal. Different products
    # can have the same ingredients, so the PoC intentionally does not match it.
    return None


def _normalized_ingredient_names(record: MedicationRecord) -> tuple[str, ...]:
    names = []
    for ingredient in _ingredients(record):
        name = _text(ingredient.get("ingredient_name_normalized"))
        if not name:
            return ()
        names.append(name)
    return tuple(sorted(names))


def _has_comparable_dose_change(
    previous: MedicationRecord, current: MedicationRecord
) -> bool:
    for field in ("dose_per_administration", "administrations_per_day"):
        if _comparable_decimal_changed(previous.get(field), current.get(field)):
            return True

    if _comparable_text_changed(previous.get("unit"), current.get("unit")):
        return True

    return _ingredient_strength_changed(previous, current)


def _ingredient_strength_changed(
    previous: MedicationRecord, current: MedicationRecord
) -> bool:
    current_ingredients = list(_ingredients(current))
    used_current: set[int] = set()

    for previous_ingredient in _ingredients(previous):
        match_index = _find_ingredient(previous_ingredient, current_ingredients, used_current)
        if match_index is None:
            continue

        used_current.add(match_index)
        current_ingredient = current_ingredients[match_index]
        if _comparable_decimal_changed(
            previous_ingredient.get("product_strength"),
            current_ingredient.get("product_strength"),
        ):
            return True
        if _comparable_text_changed(
            previous_ingredient.get("product_strength_unit"),
            current_ingredient.get("product_strength_unit"),
        ):
            return True

    return False


def _find_ingredient(
    target: MedicationRecord,
    candidates: Sequence[MedicationRecord],
    used_indices: set[int],
) -> int | None:
    target_official_id = _text(target.get("official_ingredient_id"))
    target_name = _text(target.get("ingredient_name_normalized"))

    for index, candidate in enumerate(candidates):
        if index in used_indices:
            continue
        candidate_official_id = _text(candidate.get("official_ingredient_id"))
        if target_official_id and candidate_official_id:
            if target_official_id == candidate_official_id:
                return index
            continue
        candidate_name = _text(candidate.get("ingredient_name_normalized"))
        if target_name and candidate_name and target_name == candidate_name:
            return index
    return None


def _ingredients(record: MedicationRecord) -> Sequence[MedicationRecord]:
    ingredients = record.get("ingredients")
    if not isinstance(ingredients, list):
        return ()
    return tuple(item for item in ingredients if isinstance(item, Mapping))


def _comparable_decimal_changed(left: Any, right: Any) -> bool:
    left_decimal = _decimal(left)
    right_decimal = _decimal(right)
    if left_decimal is None or right_decimal is None:
        return False
    return left_decimal != right_decimal


def _comparable_text_changed(left: Any, right: Any) -> bool:
    left_text = _text(left)
    right_text = _text(right)
    if left_text is None or right_text is None:
        return False
    return left_text != right_text


def _decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().casefold()
    return normalized or None


def _result_item(
    status: str,
    previous_record: MedicationRecord | None,
    current_record: MedicationRecord | None,
    reason_code: str,
) -> dict[str, Any]:
    return {
        "status": status,
        "previous_record": deepcopy(previous_record),
        "current_record": deepcopy(current_record),
        "reason_code": reason_code,
        "evidence": [],
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
