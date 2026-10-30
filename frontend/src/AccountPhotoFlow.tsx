import {intakeSelectionsEqual,knownSaveRejection} from './intakeEdits';
import {MfdsLookupDiagnostics} from './MfdsLookupDiagnostics';
import {useCallback,useEffect,useRef,useState} from 'react';
import {accountGeminiUpload,accountUpload,accountProcess,saveAccountResult,accountRequest} from './accountApi';
import {ImageReviewPanel} from './ImageReviewPanel';
import {confirmReviewedBatch,type ReviewState,type ExtractionResult} from './imageReviewModel';
import {ProcessingSource,MedicineReview,focusVisible} from './workflowPresentation';
import {ResultSummary,SimpleMedication,IntakeSelection} from './SimpleResult';
import {initialCurrentIntakeState,verifyCurrentIntake,type IntakeChoice,type CurrentIntakeStore} from './currentIntakeUi';
import type {PhotoResponse} from './photoApi';
import type {UploadDocument} from './uploadPhotoApi';
import type {MedicationRecord,CurrentIntakeState} from './types';
import {fileError} from './validation';
type Side='previous'|'current';
type Extracted={document:UploadDocument;results:ExtractionResult[]};
type Props={familyMemberId:string;familyLabel:string;officialMode?:'LOCAL_MOCK'|'MFDS_LIVE';syntheticAttempts?:Set<string>;onViewSaved?:(run:string)=>void;deletedRunId?:string};
export function AccountPhotoFlow(p:Props){
 const [stage,setStage]=useState<'register'|'review'|'result'>('register');
 const [files,setFiles]=useState<Partial<Record<Side,File>>>({});
 const [dates,setDates]=useState({previous:'2026-09-01',current:'2026-10-01'});
 const [source,setSource]=useState<MedicationRecord['source_type']>('MEDICINE_BAG');
 const [gemini,setGemini]=useState(false),[consent,setConsent]=useState(false),[scenario,setScenario]=useState('single');
 const [extracted,setExtracted]=useState<Partial<Record<Side,Extracted>>>({});
 const cache=useRef<Partial<Record<Side,Extracted>>>({}),localAttempts=useRef(new Set<string>());
 const attempts=p.syntheticAttempts??localAttempts.current;
 const [reviews,setReviews]=useState<Partial<Record<Side,ReviewState>>>({});
 const [ack,setAck]=useState(false),[warnAck,setWarnAck]=useState(false);
 const [result,setResult]=useState<PhotoResponse|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [saved,setSaved]=useState(false),[uncertain,setUncertain]=useState(false);
 const [savedBaseline,setSavedBaseline]=useState<Record<string,CurrentIntakeState>|null>(null),[saveFailed,setSaveFailed]=useState(false);
 const [intakes,setIntakes]=useState<CurrentIntakeStore>({});
 const operationKind=useRef('');
 const pending=useRef(false),generation=useRef(0),controller=useRef<AbortController|null>(null);
 const heading=useRef<HTMLHeadingElement|null>(null);
 useEffect(()=>()=>{generation.current++;controller.current?.abort();pending.current=false;},[]);
 useEffect(()=>{focusVisible(heading.current);},[stage,result]);
 useEffect(()=>{if(result?.account_run_id===p.deletedRunId){setResult(null);setSaved(false);setSavedBaseline(null);setStage('review');}},[p.deletedRunId]);
 const changedPrevious=useCallback((s:ReviewState)=>{setReviews(r=>({...r,previous:s}));setAck(false);setWarnAck(false);setResult(null);},[]);
 const changedCurrent=useCallback((s:ReviewState)=>{setReviews(r=>({...r,current:s}));setAck(false);setWarnAck(false);setResult(null);},[]);
 function begin(){if(pending.current)return null;pending.current=true;controller.current?.abort();const c=new AbortController();controller.current=c;const id=++generation.current;setBusy(true);setError('');return{id,c};}
 const active=(id:number,c:AbortController)=>generation.current===id&&!c.signal.aborted;
 function end(id:number){if(generation.current===id){pending.current=false;setBusy(false);}}
 function cancel(){if(operationKind.current==='save')setUncertain(true);generation.current++;controller.current?.abort();pending.current=false;setBusy(false);setError('요청 대기를 취소했습니다. 이미 전송된 요청은 끝났을 수 있습니다. 성공한 쪽은 보존하며 자동 재시도하지 않습니다.');}
 function replace(side:Side,file?:File){setFiles(x=>({...x,[side]:file}));delete cache.current[side];setExtracted({...cache.current});setReviews(x=>({...x,[side]:undefined}));setResult(null);setAck(false);setWarnAck(false);setSaved(false);setSavedBaseline(null);setSaveFailed(false);}
 async function read(){operationKind.current='read';const op=begin();if(!op)return;const{id,c}=op;
  try{for(const side of ['previous','current'] as const){
   if(cache.current[side])continue;
   const file=files[side];if(!file)throw Error('이전·현재 사진을 모두 선택하세요.');const problem=fileError(file.name,file.size,false);if(problem)throw Error(problem);
   if(gemini){if(!consent)throw Error('합성 이미지 전송 동의가 필요합니다.');if(attempts.has(side))throw Error(`${side==='previous'?'이전':'현재'} 슬롯은 이미 요청했습니다. 결과가 없어도 재호출하지 않습니다.`);attempts.add(side);}
   const timer=window.setTimeout(()=>c.abort(),65000);
   let value:Extracted;try{value=await(gemini?accountGeminiUpload(p.familyMemberId,file,dates[side],source,scenario,c.signal,{consent,side}):accountUpload(p.familyMemberId,file,dates[side],source,scenario,c.signal));}finally{window.clearTimeout(timer);}
   if(!active(id,c))return;
   if(value.results.some(r=>r.status==='FAILED'||!r.record)){setExtracted(x=>({...x,[side]:value}));throw Error(`${side==='previous'?'이전':'현재'} 사진에 읽지 못한 후보가 있습니다. 다음 요청은 실행하지 않았습니다.`);}
   cache.current[side]=value;setExtracted({...cache.current});
   if(value.results.some(r=>r.status==='NEEDS_CONFIRMATION')){if(cache.current.previous&&cache.current.current)setStage('review');throw Error('추출값 확인이 필요해 자동 진행을 멈췄습니다. 다음 사진은 자동으로 요청하지 않습니다.');}
  }
  if(active(id,c))setStage('review');
  }catch(e){if(generation.current===id)setError(c.signal.aborted?'시간 초과 또는 취소로 결과가 불명확합니다. 다음 사진을 요청하지 않았습니다. 소비한 Gemini 슬롯은 재호출하지 마세요.':e instanceof Error?e.message:'사진 읽기 실패');}
  finally{end(id);}
 }
 async function compare(warningConfirmed=false){
  const prev=confirmReviewedBatch(reviews.previous!,ack),curr=confirmReviewedBatch(reviews.current!,ack);
  if(!prev||!curr){setError('원본 대조 동의, 입력 오류 및 확인 보류 항목을 확인하세요. 확인하지 않은 후보는 확정하지 않습니다.');return;}
  operationKind.current='compare';const op=begin();if(!op)return;const{id,c}=op;
  try{const call=(confirmed:boolean)=>accountProcess(p.familyMemberId,cache.current.previous!.document,cache.current.current!.document,prev.candidates,curr.candidates,confirmed,c.signal,p.officialMode);
   let value:PhotoResponse;
   if(warningConfirmed){if(!warnAck||result?.stage!=='normalized')return;value=await call(true);}
   else{value=await call(false);if(!active(id,c))return;setResult(value);
    const rows=[...value.normalization_results.previous,...value.normalization_results.current];
    if(value.stage==='normalized'&&rows.every(r=>r.status==='MATCHED'&&!r.warnings.length&&!r.errors.length)){value=await call(true);}
   }
   if(!active(id,c))return;setResult(value);setSaved(false);setSavedBaseline(null);setSaveFailed(false);setUncertain(false);
   if(value.stage!=='normalized'){setStage('result');setIntakes({[p.familyMemberId]:Object.fromEntries(value.current_intake_states.map(s=>[s.medication_record_id,initialCurrentIntakeState(p.familyMemberId,s.medication_record_id)]))});}
  }catch(e){if(active(id,c))setError(e instanceof Error?e.message:'비교에 실패했습니다. 다시 누르기 전에 처리 상태를 확인하세요.');}finally{end(id);}
 }
 async function save(){if(!result?.account_run_id||uncertain||saved)return;operationKind.current='save';const op=begin();if(!op)return;const{id,c}=op;setSaveFailed(false);
  try{await saveAccountResult(p.familyMemberId,result.account_run_id,intakes[p.familyMemberId]??{},c.signal);if(active(id,c)){setSaved(true);setSavedBaseline(structuredClone(intakes[p.familyMemberId]??{}));}}
  catch(e){if(active(id,c)){if(knownSaveRejection(e)){setSaveFailed(true);setError('저장에 실패했습니다. 입력과 접근 권한을 확인하세요. 저장 완료로 처리하지 않았습니다.');}else{setUncertain(true);setError('저장 응답이 불명확합니다. 재전송하지 말고 저장 상태를 확인하세요.');}}}
  finally{end(id);}
 }
 async function checkSave(){if(!result?.account_run_id)return;const op=begin();if(!op)return;const{id,c}=op;try{const v=await accountRequest(`/families/${p.familyMemberId}/runs`,'GET',undefined,c.signal);if(active(id,c)){if(v.runs.some((r:{id:string})=>r.id===result.account_run_id)){const detail=await accountRequest(`/families/${p.familyMemberId}/runs/${result.account_run_id}`,'GET',undefined,c.signal);if(!active(id,c))return;const requested=Object.values(intakes[p.familyMemberId]??{}).filter(x=>x.verification_status==='USER_VERIFIED');if(requested.every(x=>detail.intake_states.some((r:{medication_record_id:string;intake_status:string;verification_status:string})=>r.medication_record_id===x.medication_record_id&&r.intake_status===x.intake_status&&r.verification_status==='USER_VERIFIED'))){const states=Object.fromEntries((detail.intake_states as CurrentIntakeState[]).map(s=>[s.medication_record_id,s]));setIntakes({[p.familyMemberId]:states});setSavedBaseline(structuredClone(states));setSaved(true);setSaveFailed(false);setError('');setUncertain(false);}else setError('자료는 있지만 선택한 복용 상태의 저장을 확인하지 못했습니다. 재전송하지 마세요.');}else setError('저장 완료가 아직 확인되지 않습니다. 다시 저장하지 말고 상태를 다시 확인하세요.');}}catch{if(active(id,c))setError('저장 상태를 확인하지 못했습니다.');}finally{end(id);}}
 function chooseIntake(id:string,choice?:IntakeChoice){
  const next=choice===undefined?{...intakes,[p.familyMemberId]:{...intakes[p.familyMemberId],[id]:savedBaseline?.[id]??initialCurrentIntakeState(p.familyMemberId,id)}}:verifyCurrentIntake(intakes,p.familyMemberId,id,choice);
  setIntakes(next);setSaved(savedBaseline!==null&&intakeSelectionsEqual(savedBaseline,next[p.familyMemberId]??{}));setSaveFailed(false);setError('');
 }
 const locked=gemini&&(['previous','current'] as const).some(s=>!cache.current[s]&&attempts.has(s));
 const valid=!locked&&files.previous&&files.current&&dates.previous&&dates.current&&(!gemini||consent);
 return <section className="simple-photo" aria-label="사진 비교 작업"><ol className="simple-steps">{['사진 등록','내용 확인','비교 결과'].map((text,i)=><li key={text} aria-current={['register','review','result'][i]===stage?'step':undefined}>{i+1}. {text}</li>)}</ol>
 {stage!=='result'&&<h2 ref={heading} tabIndex={-1}>{stage==='register'?'사진을 등록하세요':'원본과 추출 내용을 확인하세요'}</h2>}
 {error&&<p role="alert">{error}</p>}{busy&&<p role="status">처리 중… <button onClick={cancel}>작업 대기 취소</button></p>}
 <div hidden={stage!=='register'}><div className="record-pair">{(['previous','current'] as const).map(side=><section key={side}><h3>{side==='previous'?'이전':'현재'} 자료 {cache.current[side]?.results.some(r=>r.status==='NEEDS_CONFIRMATION')?'· 추출값 확인 필요':cache.current[side]?'✓ 읽기 완료':''}</h3><label>{side==='previous'?'이전':'현재'} 사진<input disabled={busy} type="file" accept=".png,.jpg,.jpeg,.webp" onChange={e=>replace(side,e.target.files?.[0])}/></label><label>{side==='previous'?'이전':'현재'} 기준일<input type="date" value={dates[side]} disabled={busy||!!cache.current[side]} onChange={e=>setDates(x=>({...x,[side]:e.target.value}))}/></label>{extracted[side]?.results.some(x=>x.status==='FAILED')&&<p role="alert">읽지 못한 후보가 있습니다. 원본과 오류를 확인하세요.</p>}</section>)}</div>
 <details><summary>고급 처리 설정</summary><label>사진 읽기 방식<select disabled={busy||!!cache.current.previous||!!cache.current.current} value={gemini?'GEMINI':'MOCK'} onChange={e=>setGemini(e.target.value==='GEMINI')}><option value="MOCK">가상 추출</option><option value="GEMINI">실제 Gemini · 관리자 합성 검증</option></select></label><label>사진 자료 유형<select disabled={busy||!!cache.current.previous||!!cache.current.current} value={source} onChange={e=>setSource(e.target.value as typeof source)}><option value="MEDICINE_BAG">약봉투</option><option value="PRESCRIPTION">처방전</option><option value="SUPPLEMENT">건강기능식품</option></select></label>{!gemini&&<label>가상 사례<select value={scenario} disabled={busy||!!cache.current.previous||!!cache.current.current} onChange={e=>setScenario(e.target.value)}><option value="single">정상</option><option value="mixed">일부 후보 실패</option><option value="unknown">함량 미확인</option></select></label>}</details>
 {gemini&&<><p className="notice">관리자·지정 합성 PNG 전용. 버튼 한 번으로 Gemini 최대 2회(이전→현재). 실패·취소 시 다음 요청과 재시도 없음. 성공한 쪽은 재사용합니다.</p><label><input type="checkbox" checked={consent} disabled={busy} onChange={e=>setConsent(e.target.checked)}/>합성 이미지 이전·현재 각 1회 전송에 동의합니다.</label></>}
 <button className="primary photo-read-action" disabled={!valid||busy} onClick={read}>사진 읽기</button>{locked&&<p role="status">슬롯을 이미 요청했지만 재사용할 결과가 없습니다. 서버 기록은 유지되며 다시 호출할 수 없습니다.</p>}{(!files.previous||!files.current)&&<p>이전·현재 사진을 모두 선택하세요.</p>}
 {Object.values(extracted).some(v=>v.results.some(r=>r.status!=='SUCCESS'))&&<details open><summary>추출 오류와 보존한 후보</summary>{Object.entries(extracted).map(([s,v])=><div key={s}><h4>{s==='previous'?'이전':'현재'}</h4>{v.results.map((r,i)=><p key={i}>{r.record?.product_name_raw??'제품 미확인'} · {r.status} · {[...r.warnings,...r.errors].map(e=>e.message).join(' ')}</p>)}</div>)}</details>}
 </div>
 <div hidden={stage!=='review'}><div className="record-pair">{(['previous','current'] as const).map(side=>extracted[side]&&<section key={side}><h3>{side==='previous'?'이전':'현재'} · {dates[side]}</h3><ImageReviewPanel disabled={busy} batchMode initialResults={extracted[side]!.results} familyMemberId={p.familyMemberId} familyLabel={p.familyLabel} sourceType={source} sourceLabel="합성 자료" recordDate={dates[side]} file={files[side]??null} uploaded account gemini={gemini} onReviewChange={side==='previous'?changedPrevious:changedCurrent}/></section>)}</div>
 <label><input type="checkbox" checked={ack} disabled={busy} onChange={e=>setAck(e.target.checked)}/>이전·현재 모든 후보를 원본과 대조했습니다. 의약품 정보에 경고가 없으면 비교까지 진행합니다.</label>
 {p.officialMode==='MFDS_LIVE'&&<p>의약품 검토·비교는 각각 별도 요청으로 실제 식약처 최대 2회입니다.</p>}
 {result?.stage==='normalized'?<><MedicineReview batches={result.normalization_results}/><label><input type="checkbox" checked={warnAck} disabled={busy} onChange={e=>setWarnAck(e.target.checked)}/>보완된 의약품 정보와 경고를 확인했습니다.</label><button disabled={busy||!ack||!warnAck} onClick={()=>compare(true)}>경고 확인 후 비교</button></>:<button className="primary" disabled={busy||!ack} onClick={()=>compare()}>내용 확인하고 비교</button>}
 <button disabled={busy} onClick={()=>setStage('register')}>사진 등록으로 돌아가기</button></div>
 {stage==='result'&&result&&<section aria-label="사진 비교 결과"><ResultSummary headingRef={heading} family={p.familyLabel} items={result.reconciliation_result?.items??null} held={result.stage==='held'} holdCount={result.pending_decisions.length} dates={`${dates.previous} → ${dates.current}`}/>{result.pending_decisions.map((d,i)=><p role="status" key={i}>{d.message}</p>)}
 {result.reconciliation_result?.items.map(item=>{const id=(item.current_record??item.previous_record)!.record_id;const state=intakes[p.familyMemberId]?.[id];return <SimpleMedication key={id} item={item}><IntakeSelection disabled={busy||uncertain} value={state?.verification_status==='USER_VERIFIED'?state.intake_status:undefined} onChange={choice=>chooseIntake(id,choice)} onClear={savedBaseline?.[id]?.verification_status!=='USER_VERIFIED'?()=>chooseIntake(id):undefined}/></SimpleMedication>})}
 <details><summary>처리 출처·원본·상세 정보</summary><ProcessingSource mode={result.mode} sources={result.extraction_sources} saved={saved} batches={result.normalization_results}/><MfdsLookupDiagnostics mode={result.mode} value={result.official_lookup}/><pre>{JSON.stringify({original:result.original_results,edited:result.edited_records,normalized:result.normalization_results},null,2)}</pre></details>
 <p>{gemini?'Gemini 추출':'가상 추출'} · {p.officialMode==='MFDS_LIVE'?'실제 식약처 요청 경로':'가상 매칭'} · {uncertain?'저장 결과 불명확':busy&&operationKind.current==='save'?'저장 중':saveFailed?'저장 실패':saved?'저장 완료':savedBaseline?'변경사항 저장 전':'저장 전'}</p>
 {result.stage==='compared'&&<button className="primary" disabled={busy||saved||uncertain} onClick={save}>{busy&&operationKind.current==='save'?'저장 중…':savedBaseline?'변경사항 저장':'저장하기'}</button>}{uncertain&&<button disabled={busy} onClick={checkSave}>저장 상태 확인</button>}{saved&&<><p role="status">✓ 저장 완료</p><button onClick={()=>p.onViewSaved?.(result.account_run_id!)}>저장 기록 보기</button></>}
 <button disabled={busy||uncertain} onClick={()=>{setStage('review');setAck(false);setResult(null);setSaved(false);setSavedBaseline(null);setSaveFailed(false);setIntakes({});}}>내용 수정으로 돌아가기</button><small className="reset-note">내용을 수정하면 화면의 비교·복용 선택만 초기화합니다. 추출 원본과 저장 기록은 유지합니다.</small></section>}
 </section>;
}
