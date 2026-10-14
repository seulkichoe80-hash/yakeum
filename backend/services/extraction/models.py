"""Internal TASK A models kept separate from the shared MedicationRecord draft."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class ExtractedIngredient:
    ingredient_name_raw: str | None = None
    product_strength: Decimal | None = None
    product_strength_unit: str | None = None


@dataclass(frozen=True)
class ExtractedMedication:
    product_name_raw: str | None = None
    ingredients: tuple[ExtractedIngredient, ...] = field(default_factory=tuple)
    unit: str | None = None
    dose_per_administration: Decimal | None = None
    administrations_per_day: Decimal | None = None
    duration_days: Decimal | None = None
    dosage_text_raw: str | None = None
    confidence: Decimal | None = None


@dataclass(frozen=True)
class ExtractedDocument:
    document_type_raw: str | None
    medications: tuple[ExtractedMedication, ...] = field(default_factory=tuple)
    claimed_family_member_id: str | None = None
