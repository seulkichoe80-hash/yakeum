// Mirror docs/DATA_SCHEMA.md. Decimal transport values stay strings.
export type Decimal = string;
export type Ingredient = {
 ingredient_name_raw: string | null; ingredient_name_normalized: string | null;
 product_strength: Decimal | null; product_strength_unit: string | null;
 official_ingredient_id: string | null;
};
export type MedicationRecord = {
 record_id: string; family_member_id: string;
 source_type: 'HIRA' | 'PRESCRIPTION' | 'MEDICINE_BAG' | 'SUPPLEMENT';
 source_record_id: string; record_date: string; dispensing_date: string | null;
 prescribing_institution: string | null; dispensing_institution: string | null;
 product_name_raw: string; product_name_normalized: string | null;
 drug_code: string | null; drug_category: string | null; unit: string | null;
 dose_per_administration: Decimal | null; administrations_per_day: Decimal | null;
 duration_days: Decimal | null; dosage_text_raw: string | null;
 mfds_product_id: string | null; ingredients: Ingredient[];
 confidence: Decimal | null; user_confirmed: boolean;
};
export const statuses = ['MAINTAINED', 'NEW', 'DOSE_CHANGED', 'NEEDS_CONFIRMATION'] as const;
export type Status = typeof statuses[number];
export const labels: Record<Status, string> = { MAINTAINED: '기록 동일', NEW: '새로 확인', DOSE_CHANGED: '복용정보 변경', NEEDS_CONFIRMATION: '이전에만 있음' };
export type ReconciliationItem = {
 status: Status; previous_record: MedicationRecord | null; current_record: MedicationRecord | null;
 reason_code: string; evidence: unknown[]; // Evidence structure is a team TODO.
};
export type ReconciliationResult = { family_member_id: string; generated_at: string; items: ReconciliationItem[] };
export type ErrorDetail = { code: string; message: string; field: string | null };
export type NormalizationStatus = 'MATCHED' | 'PARTIAL' | 'UNMATCHED' | 'FAILED';
export type NormalizationResult = {
 status: NormalizationStatus;
 record: MedicationRecord | null;
 match: { source: string | null; official_id: string | null; match_method: string | null };
 warnings: ErrorDetail[];
 errors: ErrorDetail[];
};
export type ResultBatches = { previous: NormalizationResult[]; current: NormalizationResult[] };
export type CurrentIntakeState = {
 family_member_id: string; medication_record_id: string;
 intake_status: 'TAKING' | 'NOT_TAKING' | 'UNKNOWN';
 verification_status: 'PENDING' | 'USER_VERIFIED';
 verified_by: string | null; last_verified_at: string | null;
};
export type VerticalSliceResponse = {
 processing: { parser: 'DETERMINISTIC'; file_processing: 'EXECUTED'; official_data_mode: 'LOCAL_MOCK'|'MFDS_LIVE'; persisted: false };
 accepted_results: ResultBatches;
 review_results: ResultBatches;
 reconciliation_result: ReconciliationResult;
 current_intake_states: CurrentIntakeState[];
};
export type HiraSourceRef = {side:'previous'|'current';document_id:string;input_index:number};
export type HiraV2Response = Omit<VerticalSliceResponse,'reconciliation_result'> & {
 official_lookup?:unknown;
 response_version:'TASK_D_HIRA_V2'|'TASK_D_HIRA_MFDS_V1'; family_member_id:string;
 comparison:{executed:boolean;holds:{kind:string;message:string;affected_refs:HiraSourceRef[]}[]};
 source_rows:{ref:HiraSourceRef;locator:{sheet_index:number|null;row:number|null}|null;raw_fields:Record<string,unknown>;normalization_ref:string}[];
 reconciliation_result:ReconciliationResult|null;
};
// id is a local rendering key, never part of the wire contract.
export type Item = ReconciliationItem & { id: string };
export type Member = { id: string; name: string; relationship: string; consent: boolean; approved: boolean };
export const primaryMemberId = '00000000-0000-4000-8000-000000000001';
export const initialMembers: Member[] = [
 { id: primaryMemberId, name: '가상 가족 1', relationship: '아버지', consent: true, approved: true },
 { id: '00000000-0000-4000-8000-000000000002', name: '가상 가족 2', relationship: '어머니', consent: false, approved: false }
];
export function productName(record: MedicationRecord | null): string { return record?.product_name_normalized ?? record?.product_name_raw ?? '제품 미확인'; }
export function ingredientText(record: MedicationRecord | null): string { return record?.ingredients.map(i => i.ingredient_name_normalized ?? i.ingredient_name_raw ?? '성분 미확인').join(', ') ?? '성분 미확인'; }
export function strengthText(record: MedicationRecord | null): string { return record?.ingredients.map(i => `${i.product_strength ?? '함량 미확인'} ${i.product_strength_unit ?? ''}`.trim()).join(' / ') ?? '함량 미확인'; }
