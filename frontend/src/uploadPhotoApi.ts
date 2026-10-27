import type { CandidateReview, ExtractionResult } from './imageReviewModel';
import type { MedicationRecord } from './types';
import { fileError } from './validation';
import { reviewBatch, validatePhotoResponse, type PhotoDocument, type PhotoResponse } from './photoApi';
export type UploadDocument=PhotoDocument & {upload_token:string};
const base='/api/local-demo/photo-uploads';
async function checked(response:Response) {
 const value=await response.json();
 if(!response.ok) throw new Error(typeof value.detail==='string'?value.detail:'사진 입력을 확인하고 다시 시도해 주세요.');
 if(value.response_version!=='UPLOADED_PHOTO_V1'||value.mode!=='LOCAL_MOCK'||value.persisted!==false) throw new Error('사진 응답 버전이 다릅니다. 다시 등록해 주세요.');
 return value;
}
export async function uploadPhoto(family:string,file:File,date:string,source:MedicationRecord['source_type'],scenario:string,signal:AbortSignal):Promise<{document:UploadDocument;results:ExtractionResult[]}> {
 const error=fileError(file.name,file.size,false);if(error) throw new Error(error);
 const form=new FormData();form.append('family_member_id',family);form.append('record_date',date);form.append('source_type',source);form.append('scenario',scenario);form.append('file',file);
 const value=await checked(await fetch(`${base}/extract`,{method:'POST',body:form,signal}));
 if(typeof value.upload_token!=='string'||typeof value.document_id!=='string'||!Array.isArray(value.results)||!value.results.length) throw new Error('사진 후보 응답이 올바르지 않습니다.');
 for(const r of value.results) {
  if(!['SUCCESS','NEEDS_CONFIRMATION','FAILED'].includes(r.status)||!Array.isArray(r.warnings)||!Array.isArray(r.errors)||r.record?.family_member_id&&r.record.family_member_id!==family) throw new Error('후보 가족 또는 형식이 다릅니다.');
 }
 return {document:{document_id:value.document_id,upload_token:value.upload_token,record_date:date,source_type:source,scenario:'single'},results:value.results};
}
export async function processUploads(family:string,previous:UploadDocument,current:UploadDocument,previousCandidates:CandidateReview[],currentCandidates:CandidateReview[],confirmed:boolean,signal:AbortSignal):Promise<PhotoResponse> {
 const batch=(document:UploadDocument,candidates:CandidateReview[])=>({upload_token:document.upload_token,reviews:reviewBatch(document,candidates).reviews});
 const value=await checked(await fetch(`${base}/process`,{method:'POST',headers:{'Content-Type':'application/json'},signal,body:JSON.stringify({family_member_id:family,previous:batch(previous,previousCandidates),current:batch(current,currentCandidates),normalization_confirmed:confirmed})}));
 return validatePhotoResponse(value,family);
}
