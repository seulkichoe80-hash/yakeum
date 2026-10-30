import { ResultSummary,SimpleMedication,IntakeSelection,batchDates } from './SimpleResult';
import {saveAccountResult} from './accountApi';
import {initialCurrentIntakeState,verifyCurrentIntake,type IntakeChoice} from './currentIntakeUi';
import { focusVisible, ProcessingSource } from './workflowPresentation';
import { MfdsLookupDiagnostics } from './MfdsLookupDiagnostics';
import { ComparisonBadge, ComparisonChanges, ComparisonNotice, RecordSummary } from './ComparisonDisplay';
import { useEffect, useRef, useState } from 'react';
import { accountRequest, clearAccount } from './accountApi';
import { DeleteSavedResult } from './DeleteSavedResult';
import { AccountHiraPanel } from './AccountHiraPanel';
import { AdminMfdsProbe } from './AdminMfdsProbe';
import { PhotoWorkflow } from './PhotoWorkflow';
import { labels, productName, type CurrentIntakeState, type MedicationRecord } from './types';
import { intakeChoiceLabels, verificationLabels } from './currentIntakeUi';
import { koreanSavedTime, extractionSourceLabel, officialModeLabel } from './display';
import type { PhotoResponse } from './photoApi';

type Family={id:string;name:string};
type Saved={run_id:string;family_member_id:string;result:PhotoResponse;reviews:unknown;intake_states:CurrentIntakeState[]};
export function AccountWorkspace({onExit}:{onExit?:()=>void}={}){
 const [session,setSession]=useState<{username:string}|null>(null),[checking,setChecking]=useState(true);
 const [username,setUsername]=useState(''),[password,setPassword]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>{const controller=new AbortController();const expired=()=>{setSession(null);setPassword('');};window.addEventListener('yakeum-session-expired',expired);accountRequest('/me','GET',undefined,controller.signal).then(v=>{if(!controller.signal.aborted)setSession(v);}).catch(e=>{if(!controller.signal.aborted&&!String(e).includes('로그인'))setError(e.message);}).finally(()=>{if(!controller.signal.aborted)setChecking(false);});return()=>{controller.abort();window.removeEventListener('yakeum-session-expired',expired);clearAccount();};},[]);
 async function login(register=false){setBusy(true);setError('');try{if(register)await accountRequest('/register','POST',{username,password});const v=await accountRequest('/login','POST',{username,password});setSession(v);setPassword('');}catch(e){setError(e instanceof Error?e.message:'로그인 실패');}finally{setBusy(false);}}
 async function logout(){setBusy(true);setError('');try{await accountRequest('/logout','POST');setSession(null);clearAccount();setPassword('');}catch(e){setError(e instanceof Error?e.message:'로그아웃 실패');}finally{setBusy(false);}}
 return <main className="account-workspace" style={{maxWidth:1000,margin:'20px auto',padding:20}}>
  <h1>약이음</h1>
  {error&&<p role="alert">{error}</p>}
  {checking?<p role="status">로그인 확인 중…</p>:session?<><details className="account-menu"><summary>계정</summary><p>{session.username} · 개발용 계정</p><button disabled={busy} onClick={logout}>로그아웃</button>{onExit&&<button onClick={onExit}>가상 시연 화면으로 돌아가기</button>}</details><Families key={session.username} admin={<AdminMfdsProbe key={session.username}/>}/></>:<form onSubmit={e=>{e.preventDefault();void login();}}>
   <label>가상 계정 아이디<input autoComplete="username" pattern="[a-z0-9_-]{3,40}" required value={username} onChange={e=>setUsername(e.target.value)}/></label>
   <label>비밀번호<input type="password" autoComplete="current-password" required minLength={12} maxLength={128} value={password} onChange={e=>setPassword(e.target.value)}/></label>
   <p>아이디: 영문 소문자·숫자·_·- 3~40자 / 비밀번호: 12~128자. 평소 사용하는 비밀번호를 쓰지 마세요.</p>
   <button disabled={busy||!username||password.length<12} type="submit">로그인</button><button disabled={busy||!username||password.length<12} type="button" onClick={()=>login(true)}>가상 계정 가입 후 로그인</button>
  </form>}
 </main>;
}
function Families({admin}:{admin:React.ReactNode}){
 const [detailOpen,setDetailOpen]=useState(false);
 const syntheticAttempts=useRef(new Set<string>());
 const [officialMode,setOfficialMode]=useState<'LOCAL_MOCK'|'MFDS_LIVE'>('LOCAL_MOCK');
 const [families,setFamilies]=useState<Family[]>([]),[family,setFamily]=useState(''),[name,setName]=useState(''),[error,setError]=useState('');
 useEffect(()=>{const c=new AbortController();accountRequest('/families','GET',undefined,c.signal).then(v=>{if(!c.signal.aborted){setFamilies(v.families);setFamily(v.families[0]?.id??'');}}).catch(e=>{if(!c.signal.aborted)setError(e.message);});return()=>c.abort();},[]);
 async function add(){setError('');try{const v=await accountRequest('/families','POST',{name});setFamilies(f=>[...f,v]);setFamily(v.id);setName('');}catch(e){setError(e instanceof Error?e.message:'가족 추가 실패');}}
 return <section aria-label="내 계정 가족">{error&&<p role="alert">{error}</p>}
  {families.length>0&&<label>선택 가족<select value={family} onChange={e=>{setFamily(e.target.value);setDetailOpen(false);}}>{families.map(f=><option key={f.id} value={f.id}>{f.name}</option>)}</select></label>}
  <details className="management" hidden={detailOpen} open={families.length===0}><summary>관리 · 가족 추가와 처리 설정</summary><label>가족 표시 이름<input value={name} onChange={e=>setName(e.target.value)} maxLength={60}/></label><button disabled={!name.trim()} onClick={add}>내 가족 추가</button>
  <label><input type="checkbox" checked={officialMode==='MFDS_LIVE'} onChange={e=>setOfficialMode(e.target.checked?'MFDS_LIVE':'LOCAL_MOCK')}/>실제 식약처 매칭 요청</label><p>기본은 가상 매칭입니다. 실제 경로는 별도 승인·서버 설정이 필요하며 실패를 가상 성공으로 바꾸지 않습니다. 선택 변경 시 진행 중 화면은 초기화됩니다.</p><details><summary>관리자 검증</summary>{admin}</details></details>
  {families.length>0?<FamilyWorkspace key={family+officialMode} officialMode={officialMode} syntheticAttempts={syntheticAttempts.current} family={families.find(f=>f.id===family)!} onDetailChange={setDetailOpen}/>:<p>관리에서 가상 가족을 추가하세요.</p>}
 </section>;
}

function FamilyWorkspace({family,officialMode,syntheticAttempts,onDetailChange}:{onDetailChange:(v:boolean)=>void;family:Family;officialMode:'LOCAL_MOCK'|'MFDS_LIVE';syntheticAttempts:Set<string>}){
 const [file,setFile]=useState<File|null>(null),[date,setDate]=useState('2026-10-27'),[source,setSource]=useState<MedicationRecord['source_type']>('MEDICINE_BAG');
 const [epoch,setEpoch]=useState(0),[runs,setRuns]=useState<{id:string;created:string}[]>([]),[saved,setSaved]=useState<Saved|null>(null),[error,setError]=useState('');
 const [deletedPhoto,setDeletedPhoto]=useState('');
 const [detailKind,setDetailKind]=useState<'photo'|'hira'|null>(null);
 const [choices,setChoices]=useState<Record<string,IntakeChoice>>({}),[updateUncertain,setUpdateUncertain]=useState('');
 const listPosition=useRef(0),selectedRow=useRef('');
 const openDetail=(kind:'photo'|'hira',row='')=>{listPosition.current=tab==='saved'?window.scrollY:0;selectedRow.current=row;setDetailKind(kind);onDetailChange(true);};
 const backToList=()=>{setDetailKind(null);onDetailChange(false);requestAnimationFrame(()=>{document.getElementById(selectedRow.current)?.focus({preventScroll:true});window.scrollTo(0,listPosition.current);});};
 const [tab,setTab]=useState<'photo'|'hira'|'saved'>('photo');
 const tabs=['photo','hira','saved'] as const;
 useEffect(()=>{onDetailChange(tab==='saved'&&detailKind!==null);},[tab,detailKind]);
 const [runsKnown,setRunsKnown]=useState(false);
 const [knownSources,setKnownSources]=useState<Record<string,string>>({});
 const [updating,setUpdating]=useState(false);
 const savedTitle=useRef<HTMLHeadingElement|null>(null);
 useEffect(()=>{if(saved&&detailKind==='photo'&&tab==='saved')focusVisible(savedTitle.current);},[saved,detailKind]);
 const generation=useRef(0),abort=useRef<AbortController|null>(null);
 useEffect(()=>{void loadList();return()=>{generation.current++;abort.current?.abort();};},[]);
 async function loadList(){setRunsKnown(false);const id=++generation.current;abort.current?.abort();const c=new AbortController();abort.current=c;setError('');try{const v=await accountRequest(`/families/${family.id}/runs`,'GET',undefined,c.signal);if(id===generation.current&&!c.signal.aborted){setRuns(v.runs);setRunsKnown(true);}}catch(e){if(id===generation.current&&!c.signal.aborted)setError(e instanceof Error?e.message:'목록 조회 실패');}}
 async function detail(run:string){openDetail('photo',`saved-photo-${run}`);const id=++generation.current;abort.current?.abort();const c=new AbortController();abort.current=c;setSaved(null);setError('');try{const v=await accountRequest(`/families/${family.id}/runs/${run}`,'GET',undefined,c.signal);if(id===generation.current&&!c.signal.aborted){if(v.family_member_id!==family.id)throw new Error('저장 가족이 다릅니다.');setSaved(v);if(updateUncertain!==run)setChoices({});setKnownSources(cache=>({...cache,[run]:`${extractionSourceLabel(v.result.extraction_sources?.previous??'UNKNOWN')} / ${extractionSourceLabel(v.result.extraction_sources?.current??'UNKNOWN')} · ${officialModeLabel(v.result.mode??'UNKNOWN')}`}));}}catch(e){if(id===generation.current&&!c.signal.aborted)setError(e instanceof Error?e.message:'자료 조회 실패');}}
 async function saveChanges(){if(!saved||updating||updateUncertain)return;const id=++generation.current;const c=new AbortController();abort.current?.abort();abort.current=c;setUpdating(true);setError('');const run=saved.run_id;
  try{const states=Object.fromEntries(Object.entries(choices).map(([record,choice])=>[record,verifyCurrentIntake({[family.id]:{[record]:initialCurrentIntakeState(family.id,record)}},family.id,record,choice)[family.id][record]]));await saveAccountResult(family.id,run,states,c.signal);const v=await accountRequest(`/families/${family.id}/runs/${run}`,'GET',undefined,c.signal);if(id===generation.current&&!c.signal.aborted){setSaved(v);setChoices({});}}
  catch{if(id===generation.current&&!c.signal.aborted){setUpdateUncertain(run);setError('변경 저장 결과가 불명확합니다. 다시 전송하지 말고 저장 상태를 확인하세요.');}}finally{if(id===generation.current)setUpdating(false);}}
 async function checkUpdate(){if(!saved||!updateUncertain)return;const id=++generation.current;const c=new AbortController();abort.current?.abort();abort.current=c;setUpdating(true);try{const v=await accountRequest(`/families/${family.id}/runs/${updateUncertain}`,'GET',undefined,c.signal);if(id!==generation.current||c.signal.aborted)return;setSaved(v);if(Object.entries(choices).every(([record,choice])=>v.intake_states.some((x:CurrentIntakeState)=>x.medication_record_id===record&&x.intake_status===choice&&x.verification_status==='USER_VERIFIED'))){setUpdateUncertain('');setChoices({});setError('');}else setError('모든 변경의 저장을 아직 확인하지 못했습니다. 재전송하지 말고 상태를 다시 확인하세요.');}catch{if(id===generation.current)setError('저장 상태 조회에 실패했습니다.');}finally{if(id===generation.current)setUpdating(false);}}
 async function removePhoto(run:string){
  const id=++generation.current;abort.current?.abort();const c=new AbortController();abort.current=c;
  setUpdating(true);setSaved(null);setError('');
  try{await accountRequest(`/families/${family.id}/runs/${run}`,'DELETE',undefined,c.signal);
   if(id===generation.current&&!c.signal.aborted){setRuns(rows=>rows.filter(r=>r.id!==run));setDeletedPhoto(run);backToList();}}
  catch(e){if(id===generation.current&&!c.signal.aborted)setError(e instanceof Error?e.message:'삭제 실패. 목록을 새로고침해 상태를 확인해 주세요.');}
  finally{if(id===generation.current)setUpdating(false);}
 }
 async function refreshAfterSave(){try{const v=await accountRequest(`/families/${family.id}/runs`);setRuns(v.runs);setRunsKnown(true);}catch{/* Detail remains visible if list refresh fails. */}}
 const reset=()=>{setEpoch(e=>e+1);setSaved(null);};
 return <section aria-label="로그인 가족 작업">
  <div role="tablist" aria-label="자료 작업 선택">{tabs.map((t,i)=><button type="button" key={t} id={`work-tab-${t}`} role="tab" aria-selected={tab===t} aria-controls={t==='saved'?'work-panel-saved work-hira-saved':`work-panel-${t}`} tabIndex={tab===t?0:-1} onClick={()=>setTab(t)} onKeyDown={e=>{const n=e.key==='ArrowRight'?(i+1)%3:e.key==='ArrowLeft'?(i+2)%3:e.key==='Home'?0:e.key==='End'?2:-1;if(n>=0){e.preventDefault();setTab(tabs[n]);document.getElementById(`work-tab-${tabs[n]}`)?.focus();}}}>{['사진으로 비교','HIRA로 비교','저장 기록'][i]}</button>)}</div>
  <div id="work-panel-photo" role="tabpanel" aria-labelledby="work-tab-photo" hidden={tab!=='photo'}>
  <PhotoWorkflow officialMode={officialMode} uploaded account syntheticAttempts={syntheticAttempts} onViewSaved={run=>{setTab('saved');void detail(run);void refreshAfterSave();}} deletedRunId={deletedPhoto} familyMemberId={family.id} familyLabel={family.name} sourceType={source} sourceLabel="합성 사진" recordDate={date} file={file}/>
  </div>
  <AccountHiraPanel family={family.id} name={family.name} officialMode={officialMode} tab={tab} savedDetail={detailKind==='hira'} hideSavedList={detailKind!==null} onOpenDetail={row=>openDetail('hira',row)} onBack={backToList} onViewSaved={()=>{setTab('saved');openDetail('hira');}}/>
  <div id="work-panel-saved" role="tabpanel" aria-labelledby="work-tab-saved" hidden={tab!=='saved'}>{error&&<p role="alert">{error}</p>}
  <div hidden={detailKind!==null}><h3>사진 저장 기록</h3><button disabled={updating} onClick={loadList}>저장 목록 새로고침</button>
  {runsKnown&&runs.length===0&&<p>저장된 결과가 없습니다.</p>}<ul className="saved-list">{runs.map((r,i)=><li key={r.id}><button id={`saved-photo-${r.id}`} disabled={updating||!!updateUncertain&&updateUncertain!==r.id} onClick={()=>detail(r.id)}>저장 결과 {i+1} · {koreanSavedTime(r.created)}</button><p>사진 · 처리 시각(한국 시간) · {knownSources[r.id]??'출처는 결과를 열어 확인'}</p></li>)}</ul>
  </div>{detailKind==='photo'&&<button onClick={backToList}>목록으로 돌아가기</button>}
  {detailKind==='photo'&&saved&&<section aria-label="저장된 약 정보"><ResultSummary headingRef={savedTitle} family={family.name} dates={batchDates(saved.result.normalization_results)} items={saved.result.reconciliation_result?.items??null} held={saved.result.stage==='held'}/><p role="status">{updateUncertain?'변경 저장 결과 확인 필요':Object.keys(choices).length?'자료 저장 완료 · 복용 선택 변경은 저장 전':'✓ 저장 완료'}</p>
   <p className="scope-line">사진 · {saved.result.extraction_sources?`${extractionSourceLabel(saved.result.extraction_sources.previous??'UNKNOWN')} / ${extractionSourceLabel(saved.result.extraction_sources.current??'UNKNOWN')}`:'추출 출처 확인 필요'} · {saved.result.mode==='MFDS_LIVE'?'실제 식약처 요청 경로':'가상 매칭'}</p><details><summary>처리 출처·원본 정보</summary><ProcessingSource mode={saved.result.mode} sources={saved.result.extraction_sources} saved batches={saved.result.normalization_results}/>{saved.result.mode!==officialMode&&<p role="note">현재 선택과 다른 출처의 이전 저장 결과입니다. 현재 선택은 다음 처리에만 적용됩니다.</p>}
   <MfdsLookupDiagnostics mode={saved.result.mode} value={saved.result.official_lookup}/>
   </details><details><summary>자료 삭제</summary><DeleteSavedResult key={saved.run_id} kind="사진" family={family.name} created={runs.find(r=>r.id===saved.run_id)?.created??'저장된 자료'} run={saved.run_id} busy={updating} onConfirm={()=>removePhoto(saved.run_id)}/></details>
   <details><summary>저장 원본·수정·정규화·후보 확인 구분</summary><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify({mode:saved.result.mode,official_lookup:saved.result.official_lookup,original:saved.result.original_results,edited:saved.result.edited_records,reviews:saved.reviews,normalized:saved.result.normalization_results},null,2)}</pre></details>
   {saved.result.reconciliation_result?.items.map(item=>{const record=(item.current_record??item.previous_record)!;const state=saved.intake_states.find(x=>x.medication_record_id===record.record_id);return <SimpleMedication key={record.record_id} item={item}><IntakeSelection disabled={updating||!!updateUncertain} value={choices[record.record_id]??(state?.verification_status==='USER_VERIFIED'?state.intake_status:undefined)} onChange={v=>setChoices(x=>({...x,[record.record_id]:v}))}/></SimpleMedication>;})}
   <button className="primary" disabled={updating||!Object.keys(choices).length||!!updateUncertain} onClick={saveChanges}>변경사항 저장</button>{updateUncertain&&<button disabled={updating} onClick={checkUpdate}>저장 상태 확인</button>}

  </section>}
  </div>
 </section>;
}
