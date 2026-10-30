import { AccountPhotoFlow } from './AccountPhotoFlow';
import { ProcessingSource, MedicineReview, focusVisible } from './workflowPresentation';
import { MfdsLookupDiagnostics } from './MfdsLookupDiagnostics';
import { ComparisonBadge, ComparisonChanges, ComparisonNotice, RecordSummary } from './ComparisonDisplay';
import { extractionSourceLabel, officialModeLabel } from './display';
import { useCallback, useEffect, useRef, useState } from 'react';
import { accountUpload, accountGeminiUpload, accountProcess, saveAccountResult } from './accountApi';
import { uploadPhoto, processUploads, type UploadDocument } from './uploadPhotoApi';
import { ImageReviewPanel } from './ImageReviewPanel';
import type { DemoCase, ReviewState } from './imageReviewModel';
import { extractPhoto, processPhotos, reviewBatch, type PhotoDocument, type PhotoResponse } from './photoApi';
import { initialCurrentIntakeState, intakeChoiceLabels, verificationLabels, verifyCurrentIntake, type CurrentIntakeStore, type IntakeChoice } from './currentIntakeUi';
import type { MedicationRecord } from './types';
import { labels, productName } from './types';

type Props={officialMode?:'LOCAL_MOCK'|'MFDS_LIVE';familyMemberId:string;familyLabel:string;sourceType:MedicationRecord['source_type'];sourceLabel:string;recordDate:string;file:File|null;uploaded?:boolean;account?:boolean;deletedRunId?:string;syntheticAttempts?:Set<string>;onViewSaved?:(run:string)=>void};
type Side='previous'|'current';

// Parent remounts this component on family/file/type/date changes. Within that
// session every edit or new request invalidates preview and intake confirmation.
export function PhotoWorkflow(props:Props){return props.account?<AccountPhotoFlow {...props}/>:<LegacyPhotoWorkflow {...props}/>;}
function LegacyPhotoWorkflow(props:Props) {
 const [gemini,setGemini]=useState(false);
 const [syntheticConsent,setSyntheticConsent]=useState(false);
 const localAttempts=useRef(new Set<string>());
 const attempts=props.syntheticAttempts??localAttempts.current;
 const resultTitle=useRef<HTMLHeadingElement|null>(null),currentTitle=useRef<HTMLHeadingElement|null>(null);

 const [previousFile,setPreviousFile]=useState<File|null>(null);
 const [previousDate,setPreviousDate]=useState('2026-09-01');
 const [policy,setPolicy]=useState<'normal'|'repeat'|'unknown'|'mixed'>('normal');
 const [epoch,setEpoch]=useState(0);
 const [reviews,setReviews]=useState<Partial<Record<Side,ReviewState>>>({});
 const documents=useRef<Partial<Record<Side,PhotoDocument|UploadDocument>>>({});
 const [response,setResponse]=useState<PhotoResponse|null>(null);
 useEffect(()=>{if(response)focusVisible(resultTitle.current);},[response]);
 const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 const [saved,setSaved]=useState('');
 const [intakes,setIntakes]=useState<CurrentIntakeStore>({});
 const generation=useRef(0);const abort=useRef<AbortController|null>(null);
 const invalidate=useCallback(()=>{generation.current++;abort.current?.abort();setBusy(false);setResponse(null);setIntakes({});setError('');setSaved('');},[]);
 useEffect(()=>()=>{generation.current++;abort.current?.abort();},[]);
 const changedPrevious=useCallback((state:ReviewState)=>{setReviews(r=>({...r,previous:state}));invalidate();},[invalidate]);
 const changedCurrent=useCallback((state:ReviewState)=>{setReviews(r=>({...r,current:state}));invalidate();},[invalidate]);
 const load=useCallback(async(side:Side,scenario:DemoCase,signal:AbortSignal)=>{
  invalidate();
  if(props.uploaded) {
   const file=side==='previous'?previousFile:props.file;
   if(!file) throw new Error('이전과 현재 사진을 각각 선택해 주세요.');
   if(gemini&&syntheticConsent){if(attempts.has(side))throw new Error('이 화면에서 이미 시작한 합성 검증입니다. 재호출하지 않습니다.');attempts.add(side);}
   const args=[props.familyMemberId,file,side==='previous'?previousDate:props.recordDate,props.sourceType,policy==='normal'?scenario:policy,signal] as const;
   const result=await (props.account&&gemini?accountGeminiUpload(...args,{consent:syntheticConsent,side}):(props.account?accountUpload:uploadPhoto)(...args));
   if(!signal.aborted) documents.current[side]=result.document;
   return result.results;
  }
  const document:PhotoDocument={document_id:crypto.randomUUID(),record_date:side==='previous'?previousDate:props.recordDate,source_type:props.sourceType,scenario:policy==='normal'||policy==='mixed'?scenario:policy};
  const results=await extractPhoto(props.familyMemberId,document,signal);
  if(!signal.aborted) documents.current[side]=document;
  return results;
 },[invalidate,previousDate,props.recordDate,props.sourceType,props.familyMemberId,policy,props.uploaded,props.file,previousFile,props.account,gemini,syntheticConsent,attempts]);
 const previousLoader=useCallback((scenario:DemoCase,signal:AbortSignal)=>load('previous',scenario,signal),[load]);
 const currentLoader=useCallback((scenario:DemoCase,signal:AbortSignal)=>load('current',scenario,signal),[load]);
 function reset() {invalidate();setReviews({});documents.current={};setEpoch(v=>v+1);}
 async function save() {
  if(!response?.account_run_id||busy)return;
  const controller=new AbortController();abort.current=controller;const id=++generation.current;setBusy(true);setError('');
  try {await saveAccountResult(props.familyMemberId,response.account_run_id,intakes[props.familyMemberId]??{},controller.signal);if(id===generation.current&&!controller.signal.aborted){setSaved('개발용 DB에 저장했습니다. 저장 목록 새로고침으로 다시 확인할 수 있습니다.');}}
  catch(e){if(id===generation.current&&!controller.signal.aborted)setError(e instanceof Error?e.message:'저장 실패');}
  finally{if(id===generation.current)setBusy(false);}
 }
 async function process(confirmed:boolean) {
  const previous=documents.current.previous,current=documents.current.current;
  if(!previous||!current||reviews.previous?.phase!=='ready'||reviews.current?.phase!=='ready') {setError('이전과 현재 가상 자료를 각각 추출·검토해 주세요.');return;}
  if(busy) return;
  abort.current?.abort();const controller=new AbortController();abort.current=controller;
  const id=++generation.current;setBusy(true);setError('');setResponse(null);setIntakes({});
  try {
   const value=props.uploaded ? await (props.account?accountProcess:processUploads)(props.familyMemberId,previous as UploadDocument,current as UploadDocument,reviews.previous.candidates,reviews.current.candidates,confirmed,controller.signal,props.officialMode) : await processPhotos(props.familyMemberId,reviewBatch(previous,reviews.previous.candidates),reviewBatch(current,reviews.current.candidates),confirmed,controller.signal);
   if(id!==generation.current||controller.signal.aborted) return;
   setResponse(value);
   if(value.stage==='compared') {
    const states=Object.fromEntries(value.current_intake_states.map(s=>[s.medication_record_id,initialCurrentIntakeState(props.familyMemberId,s.medication_record_id)]));
    setIntakes({[props.familyMemberId]:states});
   }
  } catch(e) {if(id===generation.current&&!controller.signal.aborted) setError(e instanceof Error?e.message:'로컬 처리 실패');}
  finally {if(id===generation.current) setBusy(false);}
 }
 useEffect(()=>{if(props.deletedRunId&&response?.account_run_id===props.deletedRunId)reset();},[props.deletedRunId,response?.account_run_id]);
 const canProcess=reviews.previous?.phase==='ready'&&reviews.current?.phase==='ready';
 return <section className="photo-workflow" aria-label={props.uploaded?'사진 업로드 전체 연결':'사진 Mock 전체 연결'}>
  <ol className="workflow-steps" aria-label="사진 비교 진행 상태">{['① 사진 선택','② 추출·내용 확인','③ 비교','④ 저장'].map((label,i)=>{const step=saved||response?.stage==='compared'?3:response||busy?2:(props.uploaded?!!previousFile&&!!props.file:reviews.previous?.phase==='ready'||reviews.current?.phase==='ready')?1:0;return <li key={label} aria-current={!saved&&step===i?'step':undefined}>{label}{saved||i<step?' ✓ 완료':i===step?' · 현재':''}</li>;})}</ol>
  <h2>사진을 읽고 내용을 확인해 주세요</h2>
  {props.account&&<label>사진 추출 방식<select value={gemini?'GEMINI':'MOCK'} onChange={e=>{setGemini(e.target.value==='GEMINI');reset();}}><option value="MOCK">가상 추출 · 실제 인식 아님</option><option value="GEMINI">Gemini · 별도 승인과 서버 설정 필요</option></select></label>}
  {gemini&&<details className="admin-tools" open><summary>관리자 합성 이미지 검증</summary><label><input type="checkbox" checked={syntheticConsent} onChange={e=>{setSyntheticConsent(e.target.checked);reset();}}/>관리자 합성 검증: 지정 PNG만 이전·현재 각 1회 전송하는 데 동의합니다. 실패·취소·재시작 후에도 재호출하지 않습니다.</label></details>}
  {gemini&&<p className="notice">Gemini 요청 경로입니다. 승인된 가상 이미지만 사용하세요. 서버 활성화·키·모델 설정이 없으면 실패하며 가상 추출로 바꾸지 않습니다. SDK 시간 제한 60초·자동 재시도 없음. 이전·현재를 각각 추출하면 Gemini 요청은 총 2회입니다. 실패·취소 후 재요청하지 마세요. 기존 실행 기록의 남은 한도는 서버가 판정하며, 이 화면이 실행 가능을 보장하지 않습니다. 추출 성공도 사용자 확인이나 정확도 보장이 아닙니다. 정규화 출처: {officialModeLabel(props.officialMode)}.</p>}
  <details><summary>사진 처리 방식과 보관 안내</summary>{props.uploaded&&!gemini?<p className="info">가상 사진만 사용하세요. PNG·JPEG·WebP, 최대 10MB · 2천만 화소 이하 정지 사진. 후보는 가짜 AI 응답이며 실제 인식 결과가 아닙니다. {props.account?'사진 파일은 저장하지 않으며 원본 후보·수정·결과는 개발용 DB에 구분해 저장합니다. 현재 계정 소유 가족에만 접근할 수 있습니다.':'사진은 영구 저장하지 않고 후보만 서버 메모리에 15분간 유지합니다. 로그인·권한 기능은 없습니다.'}</p>:!gemini&&<p className="info">가상 추출·가상 의약품 매칭 전용 · 두 가상 자료를 직접 이전/현재로 지정합니다. 가상 A 응답 → 공통 adapter → 사용자 수정 → B 정규화 → D 비교를 앱 API로 실행합니다. 이미지·키를 전송하거나 외부 API를 호출하지 않으며 결과는 저장되지 않습니다.</p>}</details>
  <label>이전 가상 자료 기준일<input type="date" value={previousDate} onChange={e=>{setPreviousDate(e.target.value);reset();}}/></label>
  {!gemini&&<label>정책 보류 검사<select value={policy} onChange={e=>{setPolicy(e.target.value as typeof policy);reset();}}><option value="normal">일반 후보</option><option value="repeat">반복 조제 · 대표 정책 미합의</option><option value="unknown">함량 미확인</option>{props.uploaded&&<option value="mixed">정상 + 숫자 오류 후보</option>}</select></label>}
  {props.uploaded&&<label>이전 사진 선택<input type="file" accept=".png,.jpg,.jpeg,.webp" onChange={e=>{setPreviousFile(e.target.files?.[0]??null);reset();}}/></label>}
  <section aria-label="이전 사진 후보"><h3>이전 자료 · {previousDate}</h3>
   <ImageReviewPanel key={`previous:${epoch}`} {...props} blockedReason={gemini?(!syntheticConsent?'합성 이미지 전송 동의가 필요합니다.':attempts.has('previous')?'이미 요청을 시작한 이전 슬롯입니다. 재호출하지 마세요.':undefined):undefined} gemini={gemini} file={props.uploaded?previousFile:null} recordDate={previousDate} loadResults={previousLoader} onReviewChange={changedPrevious}/>
  </section>
  {reviews.previous?.candidates.length&&reviews.previous.candidates.every(c=>c.user_confirmed)?<button type="button" onClick={()=>focusVisible(currentTitle.current)}>현재 사진 확인으로 이동</button>:null}
  <section aria-label="현재 사진 후보"><h3 ref={currentTitle} tabIndex={-1}>현재 자료 · {props.recordDate}</h3>
   <ImageReviewPanel key={`current:${epoch}`} {...props} blockedReason={gemini?(!syntheticConsent?'합성 이미지 전송 동의가 필요합니다.':attempts.has('current')?'이미 요청을 시작한 현재 슬롯입니다. 재호출하지 마세요.':undefined):undefined} gemini={gemini} loadResults={currentLoader} onReviewChange={changedCurrent}/>
  </section>
  <button type="button" disabled={!canProcess||busy} onClick={()=>process(false)}>확인한 내용으로 의약품 정보 검토</button>
  {busy&&<p role="status">로컬 정규화·비교 처리 중… <button onClick={invalidate}>사진 처리 취소</button></p>}
  {error&&<p role="alert">{error} 같은 버튼으로 재시도할 수 있습니다.</p>}
  {response&&(!props.deletedRunId||response.account_run_id!==props.deletedRunId)&&<section aria-label="사진 처리 결과">
   <h3 ref={resultTitle} tabIndex={-1}>사진 처리 결과 · {response.stage==='held'?'비교 보류':response.stage==='normalized'?'정규화 검토':'비교 완료'}</h3>
   <ComparisonNotice/>{response.stage==='held'&&<ComparisonBadge status="HELD"/>}
   <ProcessingSource mode={response.mode} sources={response.extraction_sources} saved={!!saved} batches={response.normalization_results}/><p>내용 확인과 실제 복용 확인은 별개입니다.</p>
   <MfdsLookupDiagnostics mode={response.mode} value={response.official_lookup}/>
   <details><summary>원본·수정 초안·정규화 결과 확인</summary><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify({mode:response.mode,official_lookup:response.official_lookup,original:response.original_results,edited:response.edited_records,normalized:response.normalization_results},null,2)}</pre></details>
   {response.pending_decisions.length>0&&<div role="status"><p>보류 사유가 있어 전체 사진 비교를 실행하지 않았습니다. 원본을 삭제하거나 신규/중단으로 판정하지 않습니다.</p><ul>{response.pending_decisions.map((p,i)=><li key={i}>{p.side}: {p.message}</li>)}</ul></div>}
   {response.stage==='normalized'&&<><MedicineReview batches={response.normalization_results}/><p>원본 내용 확인은 완료했습니다. 이제 의약품 정보의 보완값과 경고를 검토한 뒤 비교하세요.</p><button disabled={busy} onClick={()=>process(true)}>의약품 정보 확인 후 비교하기</button></>}
   {response.reconciliation_result?.items.map((item,index)=>{
    const record=item.current_record??item.previous_record;
    const id=record!.record_id;const state=intakes[props.familyMemberId]?.[id];

    return <article key={id} className="card" aria-label={`사진 비교 항목 ${index+1}`}>
     <h3>{productName(record)}</h3><ComparisonBadge status={item.status}/><ComparisonChanges item={item}/><details><summary>비교 근거</summary><p>{item.reason_code} · 의료적 복용 지시가 아닙니다.</p></details>
     <div className="record-pair"><RecordSummary side="이전" record={item.previous_record}/><RecordSummary side="현재" record={item.current_record}/></div><details><summary>사진 변경 이력</summary><p>위 이전·현재 정보는 자료 기준일별 기록이며 실제 복용 여부와 별개입니다.</p></details>
     <p>기록 비교와 별개로, 현재 실제로 복용하는지 선택해 주세요.</p>
     <h4 className="intake-heading">실제 복용 상태 선택 (기록 비교와 별도)</h4><p role="status">현재 복용: {state?intakeChoiceLabels[state.intake_status]:'잘 모르겠음'} · {state?verificationLabels[state.verification_status]:'확인 전'}</p>
     {(Object.keys(intakeChoiceLabels) as IntakeChoice[]).map(choice=><button disabled={busy} key={choice} onClick={()=>{setSaved('');setIntakes(store=>verifyCurrentIntake(store,props.familyMemberId,id,choice));}}>{intakeChoiceLabels[choice]}</button>)}
     <small>{props.account?'복용 선택을 바꾸면 저장 버튼으로 반영해 주세요. 비교 판정은 바뀌지 않습니다.':'현재 브라우저에서만 유지됩니다. 비교 결과는 바뀌지 않습니다.'}</small>
    </article>;
   })}
   {props.account&&response.stage==='compared'&&<section className="save-actions" aria-label="사진 결과 저장"><h4>④ 선택한 내용 저장</h4><p>내용 확인·기록 비교·실제 복용 선택을 구분해 보관합니다. 복용 미확인도 그대로 보존합니다.</p><button className="primary" disabled={busy||!!saved} onClick={save}>확인한 결과와 복용 선택 저장</button></section>}
   {saved&&<><p role="status">{saved}</p>{props.onViewSaved&&response.account_run_id&&<button onClick={()=>props.onViewSaved!(response.account_run_id!)}>저장한 결과 보기</button>}</>}
  </section>}
 </section>;
}
