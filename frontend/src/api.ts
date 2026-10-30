import type { MedicationRecord, VerticalSliceResponse, HiraV2Response } from './types';

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
 signal?: AbortSignal;
};

export async function requestHiraComparison(
 input: HiraComparisonInput,
 fetcher: typeof fetch = fetch,
): Promise<HiraV2Response> {
 const form = new FormData();
 form.append('family_member_id', input.familyMemberId);
 form.append('previous_file', input.previousFile);
 form.append('current_file', input.currentFile);

 const response = await fetcher('/api/v2/reconciliations/hira', {
  method: 'POST',
  body: form,
  signal: input.signal,
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
 return parseHiraV2Response(await response.json(), input.familyMemberId);
}

export function parseVerticalSliceResponse(value: unknown, expectedFamilyId: string, officialMode='LOCAL_MOCK'): VerticalSliceResponse {
 if (!['LOCAL_MOCK','MFDS_LIVE'].includes(officialMode)||!isObject(value)) throw new ApiError('Backend 응답 형식을 확인할 수 없습니다.', 502);
 const response = value as Record<string, unknown>;
 const processing = response.processing;
 if (!isObject(processing)
  || processing.parser !== 'DETERMINISTIC'
  || processing.file_processing !== 'EXECUTED'
  || processing.official_data_mode !== officialMode
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

export function parseHiraV2Response(value:unknown, family:string, officialMode='LOCAL_MOCK'):HiraV2Response {
 if(!isObject(value)||value.response_version!==(officialMode==='MFDS_LIVE'?'TASK_D_HIRA_MFDS_V1':'TASK_D_HIRA_V2')||value.family_member_id!==family
  ||!isObject(value.comparison)||typeof value.comparison.executed!=='boolean'
  ||!Array.isArray(value.comparison.holds)||!Array.isArray(value.source_rows)) throw new ApiError('HIRA v2 계약을 확인할 수 없습니다.',502);
 const held=!value.comparison.executed;
 if(held ? (value.comparison.holds.length===0||value.reconciliation_result!==null||!Array.isArray(value.current_intake_states)||value.current_intake_states.length!==0)
  : value.comparison.holds.length!==0) throw new ApiError('비교 실행/보류 결과가 일치하지 않습니다.',502);
 // Reuse all existing processing, batch, family and intake safety checks.
 parseVerticalSliceResponse(held?{...value,reconciliation_result:{family_member_id:family,generated_at:'held',items:[]}}:value,family,officialMode);
 const refKey=(ref:Record<string,unknown>)=>JSON.stringify([ref.side,ref.document_id,ref.input_index]);
 const refs=new Set<string>(); const pointers=new Set<string>();
 for(const row of value.source_rows) {
  if(!isObject(row)||!isObject(row.ref)||!['previous','current'].includes(String(row.ref.side))
   ||typeof row.ref.document_id!=='string'||!Number.isInteger(row.ref.input_index)||Number(row.ref.input_index)<0
   ||!isObject(row.raw_fields)||typeof row.normalization_ref!=='string') throw new ApiError('원본 참조가 올바르지 않습니다.',502);
  const match=/^\/(accepted_results|review_results)\/(previous|current)\/(0|[1-9]\d*)$/.exec(row.normalization_ref);
  if(!match||match[2]!==row.ref.side) throw new ApiError('정규화 참조가 올바르지 않습니다.',502);
  const batch=value[match[1]] as Record<string,unknown[]>;
  if(!batch[match[2]][Number(match[3])]||refs.has(refKey(row.ref))||pointers.has(row.normalization_ref)) throw new ApiError('정규화 참조가 중복되거나 없습니다.',502);
  refs.add(refKey(row.ref));pointers.add(row.normalization_ref);
 }
 const total=['accepted_results','review_results'].reduce((n,key)=>{const b=value[key] as Record<string,unknown[]>;return n+b.previous.length+b.current.length;},0);
 if(pointers.size!==total) throw new ApiError('원본 참조가 누락됐습니다.',502);
 for(const hold of value.comparison.holds) {
  if(!isObject(hold)||!['UNIDENTIFIED_FAILED_INPUT','UNKNOWN_COMPARISON_FIELDS','AMBIGUOUS_REPEATED_RECORDS'].includes(String(hold.kind))
   ||typeof hold.message!=='string'||!Array.isArray(hold.affected_refs)||hold.affected_refs.length===0
   ||hold.affected_refs.some((ref:unknown)=>!isObject(ref)||!refs.has(refKey(ref)))) throw new ApiError('보류 사유/원본 참조가 올바르지 않습니다.',502);
 }
 return value as HiraV2Response;
}
