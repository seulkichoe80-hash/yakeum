import type { MedicationRecord, VerticalSliceResponse } from './types';

const RECONCILIATION_STATUSES = new Set(['MAINTAINED', 'NEW', 'DOSE_CHANGED', 'NEEDS_CONFIRMATION']);
const NORMALIZATION_STATUSES = new Set(['MATCHED', 'PARTIAL', 'UNMATCHED', 'FAILED']);

export class ApiError extends Error {
 readonly status: number;

 constructor(message: string, status: number) {
  super(message);
  this.name = 'ApiError';
  this.status = status;
 }
}

export type HiraComparisonInput = {
 familyMemberId: string;
 previousFile: File;
 currentFile: File;
};

export async function requestHiraComparison(
 input: HiraComparisonInput,
 fetcher: typeof fetch = fetch,
): Promise<VerticalSliceResponse> {
 const form = new FormData();
 form.append('family_member_id', input.familyMemberId);
 form.append('previous_file', input.previousFile);
 form.append('current_file', input.currentFile);

 const response = await fetcher('/api/v1/reconciliations/hira', {
  method: 'POST',
  body: form,
 });
 if (!response.ok) {
  let message = `자료 처리 요청에 실패했습니다. (${response.status})`;
  try {
   const body = await response.json() as { detail?: unknown };
   if (typeof body.detail === 'string') message = body.detail;
  } catch {
   // Keep the status-only message when the response is not JSON.
  }
  throw new ApiError(message, response.status);
 }
 return parseVerticalSliceResponse(await response.json(), input.familyMemberId);
}

export function parseVerticalSliceResponse(value: unknown, expectedFamilyId: string): VerticalSliceResponse {
 if (!isObject(value)) throw new ApiError('Backend 응답 형식을 확인할 수 없습니다.', 502);
 const response = value as Record<string, unknown>;
 const processing = response.processing;
 if (!isObject(processing)
  || processing.parser !== 'DETERMINISTIC'
  || processing.file_processing !== 'EXECUTED'
  || processing.official_data_mode !== 'LOCAL_MOCK'
  || processing.persisted !== false) {
  throw new ApiError('Backend 처리 방식 표시가 올바르지 않습니다.', 502);
 }
 const reconciliation = response.reconciliation_result;
 if (!isObject(reconciliation)
  || reconciliation.family_member_id !== expectedFamilyId
  || typeof reconciliation.generated_at !== 'string'
  || !Array.isArray(reconciliation.items)) {
  throw new ApiError('가족별 Reconciliation 응답을 확인할 수 없습니다.', 502);
 }
 for (const item of reconciliation.items) {
  if (!isObject(item) || !RECONCILIATION_STATUSES.has(String(item.status))) {
   throw new ApiError('지원하지 않는 Reconciliation 상태입니다.', 502);
  }
  for (const record of [item.previous_record, item.current_record]) {
   if (record !== null) assertFamilyRecord(record, expectedFamilyId);
  }
 }
 assertBatches(response.accepted_results, expectedFamilyId, false);
 assertBatches(response.review_results, expectedFamilyId, true);
 if (!Array.isArray(response.current_intake_states)) {
  throw new ApiError('Current Intake State 응답을 확인할 수 없습니다.', 502);
 }
 for (const state of response.current_intake_states) {
  if (!isObject(state)
   || state.family_member_id !== expectedFamilyId
   || state.intake_status !== 'UNKNOWN'
   || state.verification_status !== 'PENDING'
   || state.verified_by !== null
   || state.last_verified_at !== null) {
   throw new ApiError('미확인 Current Intake State가 안전한 초기값이 아닙니다.', 502);
  }
 }
 return value as VerticalSliceResponse;
}

function assertBatches(value: unknown, familyId: string, failedOnly: boolean): void {
 if (!isObject(value) || !Array.isArray(value.previous) || !Array.isArray(value.current)) {
  throw new ApiError('정규화 결과 묶음을 확인할 수 없습니다.', 502);
 }
 for (const result of [...value.previous, ...value.current]) {
  if (!isObject(result) || !NORMALIZATION_STATUSES.has(String(result.status))) {
   throw new ApiError('지원하지 않는 정규화 상태입니다.', 502);
  }
  if (failedOnly && result.status !== 'FAILED') {
   throw new ApiError('처리 실패 목록에 잘못된 상태가 포함됐습니다.', 502);
  }
  if (!failedOnly && result.status === 'FAILED') {
   throw new ApiError('처리 가능 목록에 FAILED가 포함됐습니다.', 502);
  }
  if (result.record !== null) assertFamilyRecord(result.record, familyId);
  if (!Array.isArray(result.warnings) || !Array.isArray(result.errors)) {
   throw new ApiError('정규화 경고 또는 오류 형식이 올바르지 않습니다.', 502);
  }
 }
}

function assertFamilyRecord(value: unknown, familyId: string): asserts value is MedicationRecord {
 if (!isObject(value) || value.family_member_id !== familyId) {
  throw new ApiError('다른 가족의 기록이 응답에 포함됐습니다.', 502);
 }
}

function isObject(value: unknown): value is Record<string, unknown> {
 return typeof value === 'object' && value !== null && !Array.isArray(value);
}
