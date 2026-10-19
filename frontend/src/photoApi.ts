// Local experimental transport only. Shared A/B/D record contracts are unchanged.
import type { MedicationRecord, NormalizationResult, ReconciliationResult, CurrentIntakeState } from './types';
import type { CandidateReview, DemoCase, ExtractionResult } from './imageReviewModel';

export type PhotoDocument = {document_id:string;record_date:string;source_type:MedicationRecord['source_type'];scenario:DemoCase|'repeat'|'unknown'};
export type PhotoBatch = PhotoDocument & {reviews:{index:number;confirmed:boolean;draft:CandidateReview['draft']}[]};
export type PhotoResponse = {
 mode:'LOCAL_MOCK';persisted:false;stage:'normalized'|'compared'|'held';
 original_results:{previous:ExtractionResult[];current:ExtractionResult[]};
 edited_records:{previous:MedicationRecord[];current:MedicationRecord[]};
 normalization_results:{previous:NormalizationResult[];current:NormalizationResult[]};
 pending_decisions:{side:string;message:string}[];
 reconciliation_result:ReconciliationResult|null;current_intake_states:CurrentIntakeState[];
};

async function post(path:string,body:unknown,signal:AbortSignal) {
 const response=await fetch(`/api/local-demo/photos/${path}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal});
 if(!response.ok) throw new Error(`로컬 Mock 처리 실패 (${response.status}). 입력을 확인하거나 재시도해 주세요.`);
 const value=await response.json();
 if(value?.mode!=='LOCAL_MOCK'||value.persisted!==false) throw new Error('로컬 Mock 응답 형식이 다릅니다.');
 return value;
}

function checkRecord(record:MedicationRecord|null,family:string) {
 if(record!==null&&(!record||record.family_member_id!==family||typeof record.record_id!=='string'||!Array.isArray(record.ingredients))) throw new Error('가족 또는 기록 응답이 일치하지 않습니다.');
}

export async function extractPhoto(family:string,document:PhotoDocument,signal:AbortSignal):Promise<ExtractionResult[]> {
 const value=await post('extract',{family_member_id:family,...document},signal);
 if(value.document_id!==document.document_id||!Array.isArray(value.results)||value.results.length===0) throw new Error('후보 응답이 일치하지 않습니다.');
 for(const result of value.results) {
  if(!['SUCCESS','NEEDS_CONFIRMATION','FAILED'].includes(result.status)||!Array.isArray(result.warnings)||!Array.isArray(result.errors)) throw new Error('추출 결과 형식이 다릅니다.');
  checkRecord(result.record,family);
 }
 return value.results;
}

export function reviewBatch(document:PhotoDocument,candidates:CandidateReview[]):PhotoBatch {
 return {...document,reviews:candidates.map((candidate,index)=>({index,confirmed:candidate.user_confirmed,draft:structuredClone(candidate.draft)}))};
}

export async function processPhotos(family:string,previous:PhotoBatch,current:PhotoBatch,confirmed:boolean,signal:AbortSignal):Promise<PhotoResponse> {
 const value=await post('process',{family_member_id:family,previous,current,normalization_confirmed:confirmed},signal);
 if(!['normalized','compared','held'].includes(value.stage)||!Array.isArray(value.pending_decisions)||!Array.isArray(value.current_intake_states)) throw new Error('사진 처리 응답이 다릅니다.');
 for(const side of ['previous','current'] as const) {
  if(!Array.isArray(value.normalization_results?.[side])) throw new Error('정규화 응답이 다릅니다.');
  for(const result of value.normalization_results[side]) {
   if(!['MATCHED','PARTIAL','UNMATCHED','FAILED'].includes(result.status)) throw new Error('정규화 상태가 다릅니다.');
   checkRecord(result.record,family);
  }
 }
 if(value.stage==='compared') {
  if(value.reconciliation_result?.family_member_id!==family||!Array.isArray(value.reconciliation_result.items)) throw new Error('비교 가족이 다릅니다.');
  for(const item of value.reconciliation_result.items) {
   if(!['MAINTAINED','NEW','DOSE_CHANGED','NEEDS_CONFIRMATION'].includes(item.status)) throw new Error('비교 상태가 다릅니다.');
   checkRecord(item.previous_record,family);checkRecord(item.current_record,family);
  }
  for(const state of value.current_intake_states) if(state.family_member_id!==family||state.intake_status!=='UNKNOWN'||state.verification_status!=='PENDING') throw new Error('복용 상태 초기값이 다릅니다.');
 } else if(value.reconciliation_result!==null||value.current_intake_states.length) throw new Error('보류/미리보기 응답에 비교 결과가 포함됐습니다.');
 return value;
}
