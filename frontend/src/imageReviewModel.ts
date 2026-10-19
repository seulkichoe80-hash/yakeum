import type { Ingredient, MedicationRecord } from './types';

// Frontend-only Mock/draft state. Does not amend the shared API contract.
export type DemoCase = 'single' | 'multiple' | 'missing' | 'failed';
export type ExtractionStatus = 'SUCCESS' | 'NEEDS_CONFIRMATION' | 'FAILED';
export type Detail = { code: string; message: string; field: string | null };
export type ExtractionResult = { status: ExtractionStatus; record: MedicationRecord | null; warnings: Detail[]; errors: Detail[] };
export type IngredientDraft = { name: string; strength: string; unit: string; originalIndex: number | null };
export type CandidateDraft = { product: string; ingredients: IngredientDraft[]; dose: string; doseUnit: string; perDay: string; duration: string; directions: string };
export type CandidateReview = {
 key: string; original: ExtractionResult; draft: CandidateDraft;
 acknowledged: boolean; user_confirmed: boolean; deferred: boolean; attempted: boolean;
};
export type ReviewState = { phase: 'idle' | 'loading' | 'ready' | 'failed'; requestId: number; candidates: CandidateReview[]; error: string | null };
export const demoLabels: Record<DemoCase, string> = { single: '정상 제품 1개', multiple: '복수 약품 · 복수 성분', missing: '제품명·함량 누락', failed: '분석 실패' };
export const extractionLabels: Record<ExtractionStatus, string> = { SUCCESS: '후보 추출됨', NEEDS_CONFIRMATION: '추출값 확인 필요', FAILED: '추출 실패' };
export const initialReviewState = (): ReviewState => ({phase:'idle',requestId:0,candidates:[],error:null});

function ingredient(name: string, strength: string | null = '100'): Ingredient {
 return {ingredient_name_raw:name,ingredient_name_normalized:null,product_strength:strength,product_strength_unit:strength === null ? null : 'mg',official_ingredient_id:null};
}
function record(familyId: string, sourceType: MedicationRecord['source_type'], date: string, index: number): MedicationRecord {
 return {
  record_id:`10000000-0000-4000-8000-${String(index).padStart(12,'0')}`,family_member_id:familyId,
  source_type:sourceType,source_record_id:`virtual-image:${index}`,record_date:date,dispensing_date:null,
  prescribing_institution:null,dispensing_institution:null,product_name_raw:`가상 추출 제품 ${index}`,product_name_normalized:null,
  drug_code:null,drug_category:null,unit:'정',dose_per_administration:'1',administrations_per_day:'2',duration_days:'7',
  dosage_text_raw:'가상 원본 표기: 하루 두 번 한 정',mfds_product_id:null,ingredients:[ingredient(`가상 성분 ${index}`)],confidence:'0.91',user_confirmed:false,
 };
}
export function mockExtraction(kind: DemoCase, familyId: string, sourceType: MedicationRecord['source_type'], date: string): ExtractionResult[] {
 if (kind === 'failed') return [{status:'FAILED',record:null,warnings:[],errors:[{code:'AI_EXTRACTION_FAILED',message:'가상 분석 실패입니다. 파일을 전송하거나 실제 AI를 호출하지 않았습니다.',field:null}]}];
 const first = record(familyId,sourceType,date,1);
 if (kind === 'missing') return [
  {status:'NEEDS_CONFIRMATION',record:null,warnings:[{code:'REQUIRED_FIELD_MISSING',message:'제품명을 확인할 수 없습니다. 원본 후보 record가 없습니다.',field:'product_name_raw'}],errors:[]},
  {status:'NEEDS_CONFIRMATION',record:{...first,ingredients:[ingredient('가상 미확인 함량 성분',null)],confidence:null,dose_per_administration:null,administrations_per_day:null},warnings:[{code:'REQUIRED_FIELD_MISSING',message:'제품 함량과 투약 정보를 원본에서 확인해 주세요. 알 수 없는 값은 비워 두세요.',field:'ingredients'}],errors:[]},
 ];
 const result: ExtractionResult[] = [{status:'SUCCESS',record:first,warnings:[],errors:[]}];
 if (kind === 'multiple') result.push({status:'SUCCESS',record:{...record(familyId,sourceType,date,2),ingredients:[ingredient('가상 복합 성분 A','10'),ingredient('가상 복합 성분 B','20.5')]},warnings:[],errors:[]});
 return result;
}
export function draftFrom(result: ExtractionResult): CandidateDraft {
 const r = result.record;
 return { product:r?.product_name_raw ?? '',ingredients:r?.ingredients.map((i,originalIndex)=>({name:i.ingredient_name_raw ?? '',strength:i.product_strength ?? '',unit:i.product_strength_unit ?? '',originalIndex})) ?? [],dose:r?.dose_per_administration ?? '',doseUnit:r?.unit ?? '',perDay:r?.administrations_per_day ?? '',duration:r?.duration_days ?? '',directions:r?.dosage_text_raw ?? '' };
}
export function draftIssues(draft: CandidateDraft): Record<string,string> {
 const errors: Record<string,string> = {};
 if (!draft.product.trim()) errors.product = '제품명을 원본과 대조해 입력하거나 확인을 보류해 주세요.';
 const decimal = /^(?:\d+(?:\.\d*)?|\.\d+)$/;
 for (const [key,value] of [['dose',draft.dose],['perDay',draft.perDay],['duration',draft.duration]] as const) {
  if (value !== '' && !decimal.test(value)) errors[key] = '0 이상의 소수를 입력하거나 미확인이면 비워 두세요.';
 }
 if (draft.dose !== '' && !draft.doseUnit.trim()) errors.doseUnit = '1회량을 입력했다면 투약 단위를 입력해 주세요.';
 if (draft.dose === '' && draft.doseUnit.trim()) errors.dose = '투약 단위를 입력했다면 1회량도 입력해 주세요.';
 draft.ingredients.forEach((i,n)=>{
  if ((i.strength || i.unit) && !i.name.trim()) errors[`ingredient-${n}-name`] = '함량에 해당하는 성분명을 입력해 주세요.';
  if (i.strength !== '' && !decimal.test(i.strength)) errors[`ingredient-${n}-strength`] = '함량은 0 이상의 소수로 입력해 주세요.';
  if (i.strength !== '' && !i.unit.trim()) errors[`ingredient-${n}-unit`] = '함량 단위를 입력해 주세요.';
  if (i.strength === '' && i.unit.trim()) errors[`ingredient-${n}-strength`] = '함량을 입력하거나 단위도 비워 주세요.';
 });
 return errors;
}
export function changedFields(review: CandidateReview): string[] {
 const original = draftFrom(review.original);
 return (Object.keys(original) as (keyof CandidateDraft)[]).filter(key=>JSON.stringify(original[key]) !== JSON.stringify(review.draft[key]));
}
export type ReviewAction =
 | {type:'start';requestId:number}
 | {type:'finish';requestId:number;results:ExtractionResult[]}
 | {type:'reset'}
 | {type:'edit';key:string;draft:CandidateDraft}
 | {type:'acknowledge';key:string;value:boolean}
 | {type:'restore'|'confirm'|'defer';key:string};
export function reviewReducer(state: ReviewState, action: ReviewAction): ReviewState {
 if(action.type === 'reset') return initialReviewState();
 if(action.type === 'start') return state.phase === 'loading' ? state : {phase:'loading',requestId:action.requestId,candidates:[],error:null};
 if(action.type === 'finish') {
  if(state.phase !== 'loading' || state.requestId !== action.requestId) return state;
  const failed = action.results.find(r=>r.status === 'FAILED');
  if(failed) return {...state,phase:'failed',error:failed.errors[0]?.message ?? '가상 추출 실패',candidates:[]};
  return {...state,phase:'ready',error:null,candidates:action.results.map((original,n)=>({key:`candidate-${n+1}`,original,draft:draftFrom(original),acknowledged:false,user_confirmed:false,deferred:false,attempted:false}))};
 }
 return {...state,candidates:state.candidates.map(candidate=>{
  if(candidate.key !== action.key) return candidate;
  if(action.type === 'edit') return {...candidate,draft:action.draft,user_confirmed:false,acknowledged:false,deferred:false};
  if(action.type === 'acknowledge') return {...candidate,acknowledged:action.value,user_confirmed:false};
  if(action.type === 'restore') return {...candidate,draft:draftFrom(candidate.original),acknowledged:false,user_confirmed:false,deferred:false,attempted:false};
  if(action.type === 'defer') return {...candidate,deferred:true,user_confirmed:false,acknowledged:false};
  return {...candidate,attempted:true,user_confirmed:candidate.acknowledged && Object.keys(draftIssues(candidate.draft)).length === 0,deferred:false};
 })};
}
