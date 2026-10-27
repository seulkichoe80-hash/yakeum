import { useEffect, useRef, useState } from 'react';
import { accountRequest } from './accountApi';
import { parseHiraV2Response } from './api';
import { fileError } from './validation';
import { labels, productName, type HiraV2Response, type CurrentIntakeState } from './types';
import { intakeChoiceLabels, verificationLabels } from './currentIntakeUi';
import { medicationTimeline } from './timeline';

type Snapshot={run_id:string;saved:boolean;result:HiraV2Response;intake_states:CurrentIntakeState[]};
function parse(value:any,family:string):Snapshot{
 if(value.response_version!=='DEV_ACCOUNT_HIRA_V1'||value.source_type!=='HIRA'||value.family_member_id!==family||typeof value.run_id!=='string'||typeof value.saved!=='boolean')throw new Error('계정 HIRA 응답이 다릅니다.');
 const result=parseHiraV2Response(value.result,family);
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
export function AccountHiraPanel({family,name}:{family:string;name:string}){
 const [previous,setPrevious]=useState<File|null>(null),[current,setCurrent]=useState<File|null>(null);
 const [snapshot,setSnapshot]=useState<Snapshot|null>(null),[rows,setRows]=useState<{id:string;created:string}[]>([]);
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const version=useRef(0),controller=useRef<AbortController|null>(null);
 function clear(){version.current++;controller.current?.abort();setBusy(false);setSnapshot(null);setError('');setNotice('');}
 function start(clearResult:boolean){version.current++;controller.current?.abort();const c=new AbortController();controller.current=c;setBusy(true);setError('');setNotice('');if(clearResult)setSnapshot(null);return {id:version.current,c};}
 const active=(id:number,c:AbortController)=>id===version.current&&!c.signal.aborted;
 const root=`/families/${family}`;
 useEffect(()=>{void list();return()=>{version.current++;controller.current?.abort();};},[family]);
 async function list(){const {id,c}=start(true);try{const v=await accountRequest(`${root}/hira-runs`,'GET',undefined,c.signal);if(active(id,c))setRows(v.runs);}catch(e){if(active(id,c))setError(e instanceof Error?e.message:'목록 조회 실패');}finally{if(active(id,c))setBusy(false);}}
 async function process(){const {id,c}=start(true);try{
  if(!previous||!current)throw new Error('이전과 현재 XLSX 파일을 각각 선택해 주세요.');
  for(const file of [previous,current]){const e=fileError(file.name,file.size,true);if(e)throw new Error(e);}
  const body=new FormData();body.append('previous_file',previous);body.append('current_file',current);
  const v=await accountRequest(`${root}/hira/process`,'POST',body,c.signal);if(active(id,c))setSnapshot(parse(v,family));
 }catch(e){if(active(id,c))setError(e instanceof Error?e.message:'HIRA 처리 실패');}finally{if(active(id,c))setBusy(false);}}
 async function detail(run:string){const {id,c}=start(true);try{const v=await accountRequest(`${root}/hira-runs/${run}`,'GET',undefined,c.signal);if(active(id,c))setSnapshot(parse(v,family));}catch(e){if(active(id,c))setError(e instanceof Error?e.message:'저장 결과 조회 실패');}finally{if(active(id,c))setBusy(false);}}
 async function save(){if(!snapshot)return;const run=snapshot.run_id;const {id,c}=start(false);try{
  await accountRequest(`${root}/hira-runs/${run}/save`,'POST',{intake_confirmations:[]},c.signal);
  const v=await accountRequest(`${root}/hira-runs/${run}`,'GET',undefined,c.signal);
  const list=await accountRequest(`${root}/hira-runs`,'GET',undefined,c.signal);
  if(active(id,c)){setSnapshot(parse(v,family));setRows(list.runs);setNotice('HIRA 결과를 개발용 DB에 저장했습니다. 복용 확인과는 별개입니다.');}
 }catch(e){if(active(id,c))setError(e instanceof Error?e.message:'저장 실패');}finally{if(active(id,c))setBusy(false);}}
 async function verify(record:string,choice:string){if(!snapshot?.saved)return;const run=snapshot.run_id;const {id,c}=start(false);try{
  await accountRequest(`${root}/hira-runs/${run}/intake`,'PATCH',{record_id:record,choice},c.signal);
  const v=await accountRequest(`${root}/hira-runs/${run}`,'GET',undefined,c.signal);if(active(id,c))setSnapshot(parse(v,family));
 }catch(e){if(active(id,c))setError(e instanceof Error?e.message:'복용 확인 실패');}finally{if(active(id,c))setBusy(false);}}
 return <section className="card account-hira" aria-label="계정 HIRA 저장"><h2>{name} · HIRA 자료 비교·저장</h2>
  <p className="info">가상 XLSX 전용 · 로컬 SQLite · 공식 매칭은 Mock입니다. 원본 파일은 보관하지 않고 제한된 원본 행·정규화·비교 보류 사유를 저장합니다. 저장은 내용 확인이나 실제 복용 확인을 뜻하지 않습니다.</p>
  <label>이전 HIRA 파일<input type="file" accept=".xlsx" onChange={e=>{setPrevious(e.target.files?.[0]??null);clear();}}/></label>
  <label>현재 HIRA 파일<input type="file" accept=".xlsx" onChange={e=>{setCurrent(e.target.files?.[0]??null);clear();}}/></label>
  <button disabled={!previous||!current||busy} onClick={process}>HIRA 파일 처리</button>
  {busy&&<p role="status">HIRA 작업 중… <button onClick={clear}>HIRA 작업 취소</button></p>}
  {error&&<p role="alert">{error} 입력을 확인하고 같은 버튼으로 재시도해 주세요.</p>}{notice&&<p role="status">{notice}</p>}
  <h3>이 가족의 HIRA 저장 목록</h3><button disabled={busy} onClick={list}>HIRA 저장 목록 새로고침</button>
  {!rows.length&&<p>저장된 HIRA 결과가 없습니다.</p>}{rows.map((r,i)=><button disabled={busy} key={r.id} onClick={()=>detail(r.id)}>HIRA 저장 결과 {i+1} · {r.created}</button>)}
  {snapshot&&<section aria-label="계정 HIRA 결과"><h3>{snapshot.saved?'저장된 HIRA 결과':'HIRA 처리 결과'}</h3>
   {!snapshot.result.comparison.executed?<><p role="status">비교 보류 · 비교 미실행</p><ul>{snapshot.result.comparison.holds.map((h,i)=><li key={i}>{h.message} · 영향 원본 {h.affected_refs.length}건</li>)}</ul></>:<p>비교 완료 · 결과 {snapshot.result.reconciliation_result!.items.length}건</p>}
   {!snapshot.saved&&<button disabled={busy} onClick={save}>이 HIRA 결과 저장 (보류 포함)</button>}
   <details><summary>HIRA 원본·정규화·보류 사유</summary><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify({source_rows:snapshot.result.source_rows,accepted:snapshot.result.accepted_results,failed:snapshot.result.review_results,comparison:snapshot.result.comparison},null,2)}</pre></details>
   {snapshot.result.reconciliation_result?.items.map((item,index)=>{const record=item.current_record??item.previous_record;const state=snapshot.intake_states.find(s=>s.medication_record_id===record!.record_id);const t=medicationTimeline({...item,id:`hira-saved-${index}`});return <article className="card" key={record!.record_id} aria-label={`계정 HIRA 비교 항목 ${index+1}`}><h4>{productName(record)} · {labels[item.status]}</h4><p>이전: {t.previous.recordDate} · {t.previous.productStrength} · {t.previous.dosePerAdministration}</p><p>현재: {t.current.recordDate} · {t.current.productStrength} · {t.current.dosePerAdministration}</p><p>실제 복용: {state?intakeChoiceLabels[state.intake_status]:'잘 모르겠음'} · {state?verificationLabels[state.verification_status]:'확인 전'}</p>{snapshot.saved?Object.entries(intakeChoiceLabels).map(([choice,label])=><button disabled={busy} key={choice} onClick={()=>verify(record!.record_id,choice)}>{label} HIRA 저장</button>):<p>결과 저장 후 실제 복용 여부를 별도로 확인할 수 있습니다.</p>}</article>;})}
  </section>}
 </section>;
}
