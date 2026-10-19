"""Pydantic models for the internal B-D-C Vertical Slice response.

The nested team contracts remain dictionaries so this integration draft does
not redefine MedicationRecord, NormalizationResult, or ReconciliationResult.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator


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


class SourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    side: Literal["previous", "current"]
    document_id: str
    input_index: int


class Hold(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["UNIDENTIFIED_FAILED_INPUT", "UNKNOWN_COMPARISON_FIELDS", "AMBIGUOUS_REPEATED_RECORDS"]
    message: str
    affected_refs: list[SourceRef]


class ComparisonInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    executed: bool
    holds: list[Hold]


class SourceRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ref: SourceRef
    locator: dict[str, int | None] | None
    raw_fields: dict[str, Any]
    normalization_ref: str


class HiraV2Response(VerticalSliceResponse):
    response_version: Literal["TASK_D_HIRA_V2"]
    family_member_id: str
    comparison: ComparisonInfo
    source_rows: list[SourceRow]
    reconciliation_result: dict[str, Any] | None

    @model_validator(mode='after')
    def execution_consistency(self):
        if self.comparison.executed:
            if self.comparison.holds or self.reconciliation_result is None:
                raise ValueError('executed comparison requires result and no holds')
        elif not self.comparison.holds or self.reconciliation_result is not None or self.current_intake_states:
            raise ValueError('held comparison must not contain comparison/intake results')
        return self
