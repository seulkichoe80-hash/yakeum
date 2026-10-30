import { MfdsLookupDiagnostics } from './MfdsLookupDiagnostics';
import { ComparisonBadge, ComparisonChanges, ComparisonNotice, RecordSummary } from './ComparisonDisplay';
import { koreanSavedTime, officialModeLabel } from './display';
import { useEffect, useRef, useState } from 'react';
import { DeleteSavedResult } from './DeleteSavedResult';
import { accountRequest } from './accountApi';
import { parseHiraV2Response } from './api';
import { fileError } from './validation';
import { labels, productName, type HiraV2Response, type CurrentIntakeState } from './types';
import { intakeChoiceLabels, verificationLabels } from './currentIntakeUi';

type Snapshot={run_id:string;saved:boolean;result:HiraV2Response;intake_states:CurrentIntakeState[]};
function parse(value:any,family:string):Snapshot{
 if(value.response_version!=='DEV_ACCOUNT_HIRA_V1'||value.source_type!=='HIRA'||value.family_member_id!==family||typeof value.run_id!=='string'||typeof value.saved!=='boolean')throw new Error('계정 HIRA 응답이 다릅니다.');
 const mode=value.result?.processing?.official_data_mode;
 if(!['LOCAL_MOCK','MFDS_LIVE'].includes(mode))throw new Error('의약품 매칭 출처가 다릅니다.');
 const result=parseHiraV2Response(value.result,family,mode);
 const expected=new Set(result.current_intake_states.map(s=>s.medication_record_id));
 if(!Array.isArray(value.intake_states)||value.intake_states.length!==expected.size)throw new Error('저장된 복용 항목이 다릅니다.');
 const ids=new Set<string>();
 for(const s of value.intake_states){
  if(s.family_member_id!==family||!expected.has(s.medication_record_id)||ids.has(s.medication_record_id)||!['TAKING','NOT_TAKING','UNKNOWN'].includes(s.intake_status)||!['PENDING','USER_VERIFIED'].includes(s.verification_status))throw new Error('저장된 복용 확인이 다릅니다.');
  if(s.verification_status==='PENDING'&&(s.intake_status!=='UNKNOWN'||s.verified_by!==null||s.last_verified_at!==null))throw new Error('미확인 복용 상태가 다릅니다.');
  if(s.verification_status==='USER_VERIFIED'&&(!s.verified_by||!s.last_verified_at))throw new Error('복용 확인 출처가 없습니다.');
  ids.add(s.medication_record_id);
 }
 return {...value,result};
}
export function AccountHiraPanel({family,name,officialMode='LOCAL_MOCK'}:{family:string;name:string;officialMode?:'LOCAL_MOCK'|'MFDS_LIVE'}){
 const [previous,setPrevious]=useState<File|null>(null),[current,setCurrent]=useState<File|null>(null);
 const [snapshot,setSnapshot]=useState<Snapshot|null>(null),[rows,setRows]=useState<{id:string;created:string}[]>([]);
 const [rowsKnown,setRowsKnown]=useState(false);
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [deleting,setDeleting]=useState(false),[slow,setSlow]=useState(false),[uncertainRun,setUncertainRun]=useState('');
 const version=useRef(0),controller=useRef<AbortController|null>(null);
 const operation=useRef<{id:number;c:AbortController;timers:number[];saveRun?:string}|null>(null);
 const root=`/families/${family}`;
 const active=(id:number,c:AbortController)=>id===version.current&&!c.signal.aborted;
 function stopTimers(){operation.current?.timers.forEach(window.clearTimeout);}
 function interrupt(){const run=operation.current?.saveRun;stopTimers();version.current++;controller.current?.abort();operation.current=null;setBusy(false);setDeleting(false);setSlow(false);if(run)setUncertainRun(run);return run;}
 function clear(){const hadWork=busy;const run=interrupt();setSnapshot(null);setError('');setNotice(run?'저장 요청 대기를 취소했습니다. 서버에서 저장됐을 수 있으니 저장 완료 여부를 확인해 주세요.':hadWork?'HIRA 작업 대기를 취소했습니다. 결과를 다시 표시하지 않습니다.':'');}
 function start(clearResult:boolean,saveRun?:string,mutation?:'delete'|'intake'){
  interrupt();const id=version.current,c=new AbortController();controller.current=c;
  setBusy(true);setError('');setNotice('');if(clearResult)setSnapshot(null);
  const timers=[window.setTimeout(()=>{if(active(id,c))setSlow(true);},10000),window.setTimeout(()=>{
   if(!active(id,c))return;
   if(saveRun)setUncertainRun(saveRun);
   stopTimers();version.current++;c.abort();operation.current=null;setBusy(false);setDeleting(false);setSlow(false);
   setError(saveRun?'저장 응답을 확인하지 못했습니다. 다시 저장하지 말고 저장 완료 여부를 확인해 주세요.':mutation?'요청 처리 여부를 확인하지 못했습니다. 저장 목록이나 결과를 다시 열어 상태를 확인해 주세요.':'응답을 60초 동안 기다렸습니다. 서버가 깨어나는 중일 수 있습니다. 잠시 후 목록을 새로고침하거나 파일 처리를 다시 요청해 주세요.');
  },60000)];
  operation.current={id,c,timers,saveRun};return {id,c};
 }
 function finish(id:number,c:AbortController){if(active(id,c)){stopTimers();operation.current=null;setBusy(false);setDeleting(false);setSlow(false);}}
 useEffect(()=>{void list();return()=>{stopTimers();version.current++;controller.current?.abort();operation.current=null;};},[family]);
 async function list(){setRowsKnown(false);const {id,c}=start(true);try{const v=await accountRequest(`${root}/hira-runs`,'GET',undefined,c.signal);if(active(id,c)){setRows(v.runs);setRowsKnown(true);}}catch(e){if(active(id,c))setError(e instanceof Error?e.message:'목록 조회 실패');}finally{finish(id,c);}}
 async function process(){const {id,c}=start(true);try{
  if(!previous||!current)throw new Error('이전과 현재 XLSX 파일을 각각 선택해 주세요.');
  for(const file of [previous,current]){const e=fileError(file.name,file.size,true);if(e)throw new Error(e);}
  const body=new FormData();body.append('previous_file',previous);body.append('current_file',current);body.append('official_mode',officialMode);
  const v=await accountRequest(`${root}/hira/process`,'POST',body,c.signal);if(active(id,c)){if(v.result?.processing?.official_data_mode!==officialMode)throw new Error('요청한 의약품 매칭 출처와 응답이 다릅니다.');setSnapshot(parse(v,family));}
 }catch(e){if(active(id,c))setError(e instanceof Error?e.message:'HIRA 처리 실패');}finally{finish(id,c);}}
 async function detail(run:string){const {id,c}=start(true);try{const v=await accountRequest(`${root}/hira-runs/${run}`,'GET',undefined,c.signal);if(active(id,c))setSnapshot(parse(v,family));}catch(e){if(active(id,c))setError(e instanceof Error?e.message:'저장 결과 조회 실패');}finally{finish(id,c);}}
 async function save(){if(!snapshot||busy||uncertainRun)return;const run=snapshot.run_id;const {id,c}=start(false,run);try{
  await accountRequest(`${root}/hira-runs/${run}/save`,'POST',{intake_confirmations:[]},c.signal);
  const v=await accountRequest(`${root}/hira-runs/${run}`,'GET',undefined,c.signal);
  const list=await accountRequest(`${root}/hira-runs`,'GET',undefined,c.signal);
  if(active(id,c)){setSnapshot(parse(v,family));setRows(list.runs);setRowsKnown(true);setUncertainRun('');setNotice('HIRA 결과를 개발용 DB에 저장했습니다. 복용 확인과는 별개입니다.');}
 }catch(e){if(active(id,c)){setUncertainRun(run);setError('저장 요청 결과를 확인하지 못했습니다. 중복 요청을 피하도록 저장 완료 여부부터 확인해 주세요.');}}finally{finish(id,c);}}
 async function checkSave(){if(!uncertainRun||busy)return;const run=uncertainRun;const {id,c}=start(false);try{
  const list=await accountRequest(`${root}/hira-runs`,'GET',undefined,c.signal);
  if(!active(id,c))return;setRows(list.runs);setRowsKnown(true);
  if(!list.runs.some((r:{id:string})=>r.id===run)){setNotice('아직 저장 완료가 확인되지 않았습니다. 저장을 다시 보내지 말고 잠시 후 완료 여부를 다시 확인해 주세요.');return;}
  const v=await accountRequest(`${root}/hira-runs/${run}`,'GET',undefined,c.signal);
  if(active(id,c)){setSnapshot(parse(v,family));setUncertainRun('');setNotice('저장된 결과를 확인했습니다. 저장 요청을 다시 보내지 않았습니다.');}
 }catch(e){if(active(id,c))setError('저장 상태 조회에 실패했습니다. 잠시 후 완료 여부를 다시 확인해 주세요.');}finally{finish(id,c);}}
 async function remove(){
  if(!snapshot?.saved)return;const run=snapshot.run_id;const {id,c}=start(true,undefined,'delete');setDeleting(true);
  try{await accountRequest(`${root}/hira-runs/${run}`,'DELETE',undefined,c.signal);
   if(active(id,c)){setRows(rows=>rows.filter(r=>r.id!==run));setNotice('선택한 HIRA 결과와 연결된 복용 확인을 삭제했습니다.');}}
  catch(e){if(active(id,c))setError('삭제 결과를 확인하지 못했습니다. 목록을 새로고침해 상태를 확인해 주세요.');}
  finally{finish(id,c);}
 }
 async function verify(record:string,choice:string){if(!snapshot?.saved)return;const run=snapshot.run_id;const {id,c}=start(false,undefined,'intake');try{
  await accountRequest(`${root}/hira-runs/${run}/intake`,'PATCH',{record_id:record,choice},c.signal);
  const v=await accountRequest(`${root}/hira-runs/${run}`,'GET',undefined,c.signal);if(active(id,c))setSnapshot(parse(v,family));
 }catch(e){if(active(id,c))setError('복용 확인 결과를 확인하지 못했습니다. 저장된 결과를 다시 열어 확인해 주세요.');}finally{finish(id,c);}}
 return <section className="card account-hira" aria-label="계정 HIRA 저장"><h2>{name} · HIRA 자료 비교·저장</h2>
  <p className="info">가상 XLSX 전용 · 개발용 DB · {officialModeLabel(officialMode)}. 원본 파일은 보관하지 않고 제한된 원본 행·정규화·비교 보류 사유를 저장합니다. 저장은 내용 확인이나 실제 복용 확인을 뜻하지 않습니다.</p>
  <label>이전 HIRA 파일<input type="file" disabled={deleting} accept=".xlsx" onChange={e=>{setPrevious(e.target.files?.[0]??null);clear();}}/></label>
  <label>현재 HIRA 파일<input type="file" disabled={deleting} accept=".xlsx" onChange={e=>{setCurrent(e.target.files?.[0]??null);clear();}}/></label>
  <button disabled={!previous||!current||busy} onClick={process}>HIRA 파일 처리</button>
  {busy&&<p role="status">HIRA 작업 중… {!deleting&&<button onClick={clear}>HIRA 작업 취소</button>}</p>}
  {slow&&busy&&<p role="status">응답이 지연되고 있습니다. 무료 서버가 깨어나는 중일 수 있습니다. 잠시 기다리거나 작업 대기를 취소할 수 있습니다.</p>}
  {uncertainRun&&<p role="status">저장 완료 여부 확인이 필요합니다. <button disabled={busy} onClick={checkSave}>HIRA 저장 완료 여부 확인</button></p>}
  {error&&<p role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}
  <h3>이 가족의 HIRA 저장 목록</h3><button disabled={busy} onClick={list}>HIRA 저장 목록 새로고침</button>
  {rowsKnown&&!rows.length&&<p>저장된 HIRA 결과가 없습니다.</p>}{rows.map((r,i)=><button disabled={busy} key={r.id} onClick={()=>detail(r.id)}>HIRA 저장 결과 {i+1} · {koreanSavedTime(r.created)}</button>)}
  {snapshot&&<section aria-label="계정 HIRA 결과"><p>{officialModeLabel(snapshot.result.processing.official_data_mode)}</p><MfdsLookupDiagnostics mode={snapshot.result.processing.official_data_mode} value={snapshot.result.official_lookup}/><h3>{snapshot.saved?'저장된 HIRA 결과':'HIRA 처리 결과'}</h3>{snapshot.saved&&snapshot.result.processing.official_data_mode!==officialMode&&<p role="note" aria-label="이전 저장 결과 안내">현재 선택과 다른 출처의 이전 저장 결과입니다. 체크 상태는 다음 처리에만 적용되며, 아래 결과는 그 선택으로 새로 처리한 결과가 아닙니다.</p>}<ComparisonNotice/>
   {snapshot.saved&&<DeleteSavedResult key={snapshot.run_id} kind="HIRA" family={name} created={rows.find(r=>r.id===snapshot.run_id)?.created??'저장된 자료'} run={snapshot.run_id} busy={busy} onConfirm={remove}/>}
   {!snapshot.result.comparison.executed?<><ComparisonBadge status="HELD"/><p role="status">비교 보류 · 비교 미실행</p><ul>{snapshot.result.comparison.holds.map((h,i)=><li key={i}>{h.message} · 영향 원본 {h.affected_refs.length}건</li>)}</ul></>:<p>비교 완료 · 결과 {snapshot.result.reconciliation_result!.items.length}건</p>}
   {!snapshot.saved&&<button disabled={busy||!!uncertainRun} onClick={save}>이 HIRA 결과 저장 (보류 포함)</button>}
   <details><summary>HIRA 원본·정규화·보류 사유</summary><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify({response_version:snapshot.result.response_version,processing:snapshot.result.processing,official_lookup:snapshot.result.official_lookup,source_rows:snapshot.result.source_rows,accepted:snapshot.result.accepted_results,failed:snapshot.result.review_results,comparison:snapshot.result.comparison},null,2)}</pre></details>
   {snapshot.result.reconciliation_result?.items.map((item,index)=>{const record=item.current_record??item.previous_record;const state=snapshot.intake_states.find(s=>s.medication_record_id===record!.record_id);return <article className="card" key={record!.record_id} aria-label={`계정 HIRA 비교 항목 ${index+1}`}><h4>{productName(record)}</h4><ComparisonBadge status={item.status}/><ComparisonChanges item={item}/><RecordSummary side="이전" record={item.previous_record}/><RecordSummary side="현재" record={item.current_record}/><p>실제 복용: {state?intakeChoiceLabels[state.intake_status]:'잘 모르겠음'} · {state?verificationLabels[state.verification_status]:'확인 전'}</p>{snapshot.saved?Object.entries(intakeChoiceLabels).map(([choice,label])=><button disabled={busy} key={choice} onClick={()=>verify(record!.record_id,choice)}>{label} HIRA 저장</button>):<p>결과 저장 후 실제 복용 여부를 별도로 확인할 수 있습니다.</p>}</article>;})}
  </section>}
 </section>;
}
