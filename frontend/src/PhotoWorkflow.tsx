import { useCallback, useEffect, useRef, useState } from 'react';
import { uploadPhoto, processUploads, type UploadDocument } from './uploadPhotoApi';
import { ImageReviewPanel } from './ImageReviewPanel';
import type { DemoCase, ReviewState } from './imageReviewModel';
import { extractPhoto, processPhotos, reviewBatch, type PhotoDocument, type PhotoResponse } from './photoApi';
import { initialCurrentIntakeState, intakeChoiceLabels, verificationLabels, verifyCurrentIntake, type CurrentIntakeStore, type IntakeChoice } from './currentIntakeUi';
import { medicationTimeline } from './timeline';
import type { MedicationRecord } from './types';
import { labels, productName } from './types';

type Props={familyMemberId:string;familyLabel:string;sourceType:MedicationRecord['source_type'];sourceLabel:string;recordDate:string;file:File|null;uploaded?:boolean};
type Side='previous'|'current';

// Parent remounts this component on family/file/type/date changes. Within that
// session every edit or new request invalidates preview and intake confirmation.
export function PhotoWorkflow(props:Props) {
 const [previousFile,setPreviousFile]=useState<File|null>(null);
 const [previousDate,setPreviousDate]=useState('2026-09-01');
 const [policy,setPolicy]=useState<'normal'|'repeat'|'unknown'|'mixed'>('normal');
 const [epoch,setEpoch]=useState(0);
 const [reviews,setReviews]=useState<Partial<Record<Side,ReviewState>>>({});
 const documents=useRef<Partial<Record<Side,PhotoDocument|UploadDocument>>>({});
 const [response,setResponse]=useState<PhotoResponse|null>(null);
 const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 const [intakes,setIntakes]=useState<CurrentIntakeStore>({});
 const generation=useRef(0);const abort=useRef<AbortController|null>(null);
 const invalidate=useCallback(()=>{generation.current++;abort.current?.abort();setBusy(false);setResponse(null);setIntakes({});setError('');},[]);
 useEffect(()=>()=>{generation.current++;abort.current?.abort();},[]);
 const changedPrevious=useCallback((state:ReviewState)=>{setReviews(r=>({...r,previous:state}));invalidate();},[invalidate]);
 const changedCurrent=useCallback((state:ReviewState)=>{setReviews(r=>({...r,current:state}));invalidate();},[invalidate]);
 const load=useCallback(async(side:Side,scenario:DemoCase,signal:AbortSignal)=>{
  invalidate();
  if(props.uploaded) {
   const file=side==='previous'?previousFile:props.file;
   if(!file) throw new Error('이전과 현재 사진을 각각 선택해 주세요.');
   const result=await uploadPhoto(props.familyMemberId,file,side==='previous'?previousDate:props.recordDate,props.sourceType,policy==='normal'?scenario:policy,signal);
   if(!signal.aborted) documents.current[side]=result.document;
   return result.results;
  }
  const document:PhotoDocument={document_id:crypto.randomUUID(),record_date:side==='previous'?previousDate:props.recordDate,source_type:props.sourceType,scenario:policy==='normal'||policy==='mixed'?scenario:policy};
  const results=await extractPhoto(props.familyMemberId,document,signal);
  if(!signal.aborted) documents.current[side]=document;
  return results;
 },[invalidate,previousDate,props.recordDate,props.sourceType,props.familyMemberId,policy,props.uploaded,props.file,previousFile]);
 const previousLoader=useCallback((scenario:DemoCase,signal:AbortSignal)=>load('previous',scenario,signal),[load]);
 const currentLoader=useCallback((scenario:DemoCase,signal:AbortSignal)=>load('current',scenario,signal),[load]);
 function reset() {invalidate();setReviews({});documents.current={};setEpoch(v=>v+1);}
 async function process(confirmed:boolean) {
  const previous=documents.current.previous,current=documents.current.current;
  if(!previous||!current||reviews.previous?.phase!=='ready'||reviews.current?.phase!=='ready') {setError('이전과 현재 가상 자료를 각각 추출·검토해 주세요.');return;}
  if(busy) return;
  abort.current?.abort();const controller=new AbortController();abort.current=controller;
  const id=++generation.current;setBusy(true);setError('');setResponse(null);setIntakes({});
  try {
   const value=props.uploaded ? await processUploads(props.familyMemberId,previous as UploadDocument,current as UploadDocument,reviews.previous.candidates,reviews.current.candidates,confirmed,controller.signal) : await processPhotos(props.familyMemberId,reviewBatch(previous,reviews.previous.candidates),reviewBatch(current,reviews.current.candidates),confirmed,controller.signal);
   if(id!==generation.current||controller.signal.aborted) return;
   setResponse(value);
   if(value.stage==='compared') {
    const states=Object.fromEntries(value.current_intake_states.map(s=>[s.medication_record_id,initialCurrentIntakeState(props.familyMemberId,s.medication_record_id)]));
    setIntakes({[props.familyMemberId]:states});
   }
  } catch(e) {if(id===generation.current&&!controller.signal.aborted) setError(e instanceof Error?e.message:'로컬 처리 실패');}
  finally {if(id===generation.current) setBusy(false);}
 }
 const canProcess=reviews.previous?.phase==='ready'&&reviews.current?.phase==='ready';
 return <section className="photo-workflow" aria-label={props.uploaded?'사진 업로드 전체 연결':'사진 Mock 전체 연결'}>
  <h2>{props.uploaded?'사진 업로드 · 가짜 AI 연결 검사':'사진 Mock 전체 연결 검증'}</h2>
  {props.uploaded?<p className="info">가상 사진만 사용하세요. PNG·JPEG·WebP, 최대 10MB · 2천만 화소 이하 정지 사진. 후보는 가짜 AI 응답이며 실제 인식 결과가 아닙니다. 사진은 영구 저장하지 않고 후보만 서버 메모리에 15분간 유지합니다. 로그인·권한 기능은 없습니다.</p>:<p className="info">LOCAL_MOCK 전용 · 두 가상 자료를 직접 이전/현재로 지정합니다. 가상 A 응답 → 공통 adapter → 사용자 수정 → B 정규화 → D 비교를 실제 로컬 API로 실행합니다. 이미지·키를 전송하거나 외부 API를 호출하지 않으며 결과는 저장되지 않습니다.</p>}
  <label>이전 가상 자료 기준일<input type="date" value={previousDate} onChange={e=>{setPreviousDate(e.target.value);reset();}}/></label>
  <label>정책 보류 검사<select value={policy} onChange={e=>{setPolicy(e.target.value as typeof policy);reset();}}><option value="normal">일반 후보</option><option value="repeat">반복 조제 · 대표 정책 미합의</option><option value="unknown">함량 미확인</option>{props.uploaded&&<option value="mixed">정상 + 숫자 오류 후보</option>}</select></label>
  {props.uploaded&&<label>이전 사진 선택<input type="file" accept=".png,.jpg,.jpeg,.webp" onChange={e=>{setPreviousFile(e.target.files?.[0]??null);reset();}}/></label>}
  <section aria-label="이전 사진 후보"><h3>이전 가상 자료 (직접 지정)</h3>
   <ImageReviewPanel key={`previous:${epoch}`} {...props} file={props.uploaded?previousFile:null} recordDate={previousDate} loadResults={previousLoader} onReviewChange={changedPrevious}/>
  </section>
  <section aria-label="현재 사진 후보"><h3>현재 가상 자료 (직접 지정)</h3>
   <ImageReviewPanel key={`current:${epoch}`} {...props} loadResults={currentLoader} onReviewChange={changedCurrent}/>
  </section>
  <button type="button" disabled={!canProcess||busy} onClick={()=>process(false)}>수정 후보 B 정규화 미리보기</button>
  {busy&&<p role="status">로컬 정규화·비교 처리 중… <button onClick={invalidate}>사진 처리 취소</button></p>}
  {error&&<p role="alert">{error} 같은 버튼으로 재시도할 수 있습니다.</p>}
  {response&&<section aria-label="사진 처리 결과">
   <h3>사진 처리 결과 · {response.stage==='held'?'비교 보류':response.stage==='normalized'?'정규화 검토':'비교 완료'}</h3>
   <p>LOCAL_MOCK · 실제 AI/식약처 조회 없음 · 새로고침하면 사라집니다.</p>
   <details><summary>원본·수정 초안·정규화 결과 확인</summary><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify({original:response.original_results,edited:response.edited_records,normalized:response.normalization_results},null,2)}</pre></details>
   {response.pending_decisions.length>0&&<div role="status"><p>보류 사유가 있어 전체 사진 비교를 실행하지 않았습니다. 원본을 삭제하거나 신규/중단으로 판정하지 않습니다.</p><ul>{response.pending_decisions.map((p,i)=><li key={i}>{p.side}: {p.message}</li>)}</ul></div>}
   {response.stage==='normalized'&&<><p>추출 내용 대조와 정규화 결과 확인은 다릅니다. 보완값·경고를 검토한 뒤 진행하세요.</p><button disabled={busy} onClick={()=>process(true)}>정규화 결과 확인 후 D 비교</button></>}
   {response.reconciliation_result?.items.map((item,index)=>{
    const record=item.current_record??item.previous_record;
    const id=record!.record_id;const state=intakes[props.familyMemberId]?.[id];
    const timeline=medicationTimeline({...item,id:`photo-${index}`});
    return <article key={id} className="card" aria-label={`사진 비교 항목 ${index+1}`}>
     <h3>{productName(record)} · {labels[item.status]}</h3><p>{item.reason_code} · 의료적 복용 지시가 아닙니다.</p>
     <details><summary>사진 변경 이력</summary><p>이전: {timeline.previous.recordDate} · {timeline.previous.productStrength} · {timeline.previous.dosePerAdministration}</p><p>현재: {timeline.current.recordDate} · {timeline.current.productStrength} · {timeline.current.dosePerAdministration}</p></details>
     <p>추출·정규화 확인과 별개로 실제 복용 여부를 직접 선택해 주세요.</p>
     <p role="status">현재 복용: {state?intakeChoiceLabels[state.intake_status]:'잘 모르겠음'} · {state?verificationLabels[state.verification_status]:'확인 전'}</p>
     {(Object.keys(intakeChoiceLabels) as IntakeChoice[]).map(choice=><button key={choice} onClick={()=>setIntakes(store=>verifyCurrentIntake(store,props.familyMemberId,id,choice))}>{intakeChoiceLabels[choice]}</button>)}
     <small>현재 브라우저에서만 유지됩니다. 비교 결과는 바뀌지 않습니다.</small>
    </article>;
   })}
  </section>}
 </section>;
}
