"""Pydantic models for the internal B-D-C Vertical Slice response.

The nested team contracts remain dictionaries so this integration draft does
not redefine MedicationRecord, NormalizationResult, or ReconciliationResult.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ProcessingInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parser: Literal["DETERMINISTIC"]
    file_processing: Literal["EXECUTED"]
    official_data_mode: Literal["LOCAL_MOCK"]
    persisted: Literal[False]


class ResultBatches(BaseModel):
    model_config = ConfigDict(extra="forbid")

    previous: list[dict[str, Any]]
    current: list[dict[str, Any]]


class VerticalSliceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    processing: ProcessingInfo
    accepted_results: ResultBatches
    review_results: ResultBatches
    reconciliation_result: dict[str, Any]
    current_intake_states: list[dict[str, Any]]
