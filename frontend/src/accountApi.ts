import type { CandidateReview, ExtractionResult } from './imageReviewModel';
import type { CurrentIntakeState, MedicationRecord } from './types';
import { fileError } from './validation';
import { reviewBatch, validatePhotoResponse, type PhotoResponse } from './photoApi';
import type { UploadDocument } from './uploadPhotoApi';
let csrf='';
export function clearAccount(){csrf='';}
export async function accountRequest(path:string,method='GET',body?:unknown,signal?:AbortSignal):Promise<any>{
 const headers:Record<string,string>={};if(csrf)headers['X-CSRF-Token']=csrf;
 if(body!==undefined&&!(body instanceof FormData))headers['Content-Type']='application/json';
 const response=await fetch(`/api/dev-account${path}`,{method,headers,credentials:'same-origin',cache:'no-store',body:body instanceof FormData?body:body===undefined?undefined:JSON.stringify(body),signal});
 const value=await response.json();
 if(!response.ok){if(response.status===401){csrf='';window.dispatchEvent(new Event('yakeum-session-expired'));}throw new Error(typeof value.detail==='string'?value.detail:'입력 형식을 확인하고 다시 시도해 주세요.');}
 if(value.csrf_token)csrf=value.csrf_token;
 return value;
}
export async function accountUpload(family:string,file:File,date:string,source:MedicationRecord['source_type'],scenario:string,signal:AbortSignal):Promise<{document:UploadDocument;results:ExtractionResult[]}>{
 const error=fileError(file.name,file.size,false);if(error)throw new Error(error);
 const body=new FormData();body.append('file',file);body.append('record_date',date);body.append('source_type',source);body.append('scenario',scenario);
 const v=await accountRequest(`/families/${family}/photos/extract`,'POST',body,signal);
 if(v.response_version!=='DEV_ACCOUNT_V1'||!Array.isArray(v.results)||!v.results.length)throw new Error('개발용 사진 응답이 올바르지 않습니다.');
 for(const r of v.results)if(r.record&&r.record.family_member_id!==family)throw new Error('후보 가족이 다릅니다.');
 return {document:{document_id:v.document_id,upload_token:v.document_id,record_date:date,source_type:source,scenario:'single'},results:v.results};
}
export async function accountProcess(family:string,previous:UploadDocument,current:UploadDocument,p:CandidateReview[],c:CandidateReview[],confirmed:boolean,signal:AbortSignal):Promise<PhotoResponse>{
 const batch=(d:UploadDocument,c:CandidateReview[])=>({document_id:d.document_id,reviews:reviewBatch(d,c).reviews});
 const v=await accountRequest(`/families/${family}/photos/process`,'POST',{previous:batch(previous,p),current:batch(current,c),normalization_confirmed:confirmed},signal);
 if(v.response_version!=='DEV_ACCOUNT_V1'||typeof v.run_id!=='string')throw new Error('저장 준비 응답이 다릅니다.');
 return {...validatePhotoResponse(v.result,family),account_run_id:v.run_id};
}
export async function saveAccountResult(family:string,run:string,states:Record<string,CurrentIntakeState>,signal:AbortSignal){
 const intake_confirmations=Object.values(states).filter(s=>s.verification_status==='USER_VERIFIED').map(s=>({record_id:s.medication_record_id,choice:s.intake_status}));
 return accountRequest(`/families/${family}/runs/${run}/save`,'POST',{intake_confirmations},signal);
}
