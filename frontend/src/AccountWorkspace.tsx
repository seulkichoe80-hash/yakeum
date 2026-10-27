import { useEffect, useRef, useState } from 'react';
import { accountRequest, clearAccount } from './accountApi';
import { PhotoWorkflow } from './PhotoWorkflow';
import { labels, productName, type CurrentIntakeState, type MedicationRecord } from './types';
import { intakeChoiceLabels, verificationLabels } from './currentIntakeUi';
import { medicationTimeline } from './timeline';
import type { PhotoResponse } from './photoApi';

type Family={id:string;name:string};
type Saved={run_id:string;family_member_id:string;result:PhotoResponse;reviews:unknown;intake_states:CurrentIntakeState[]};
export function AccountWorkspace(){
 const [session,setSession]=useState<{username:string}|null>(null),[checking,setChecking]=useState(true);
 const [username,setUsername]=useState(''),[password,setPassword]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>{const controller=new AbortController();const expired=()=>{setSession(null);setPassword('');};window.addEventListener('yakeum-session-expired',expired);accountRequest('/me','GET',undefined,controller.signal).then(v=>{if(!controller.signal.aborted)setSession(v);}).catch(e=>{if(!controller.signal.aborted&&!String(e).includes('로그인'))setError(e.message);}).finally(()=>{if(!controller.signal.aborted)setChecking(false);});return()=>{controller.abort();window.removeEventListener('yakeum-session-expired',expired);clearAccount();};},[]);
 async function login(register=false){setBusy(true);setError('');try{if(register)await accountRequest('/register','POST',{username,password});const v=await accountRequest('/login','POST',{username,password});setSession(v);setPassword('');}catch(e){setError(e instanceof Error?e.message:'로그인 실패');}finally{setBusy(false);}}
 async function logout(){setBusy(true);setError('');try{await accountRequest('/logout','POST');setSession(null);clearAccount();setPassword('');}catch(e){setError(e instanceof Error?e.message:'로그아웃 실패');}finally{setBusy(false);}}
 return <main className="account-workspace" style={{maxWidth:1000,margin:'20px auto',padding:20}}>
  <h1>개발용 로그인·저장</h1><p className="notice">가상 사용자·가상 자료 전용 · 로컬 SQLite · 실제 AI/공식 조회 없음. 운영용 인증·저장 기능은 아닙니다.</p>
  {error&&<p role="alert">{error}</p>}
  {checking?<p role="status">로그인 확인 중…</p>:session?<><p>로그인: {session.username} <button disabled={busy} onClick={logout}>로그아웃</button></p><Families key={session.username}/></>:<form onSubmit={e=>{e.preventDefault();void login();}}>
   <label>가상 계정 아이디<input autoComplete="username" pattern="[a-z0-9_-]{3,40}" required value={username} onChange={e=>setUsername(e.target.value)}/></label>
   <label>비밀번호<input type="password" autoComplete="current-password" required minLength={12} maxLength={128} value={password} onChange={e=>setPassword(e.target.value)}/></label>
   <p>아이디: 영문 소문자·숫자·_·- 3~40자 / 비밀번호: 12~128자. 평소 사용하는 비밀번호를 쓰지 마세요.</p>
   <button disabled={busy||!username||password.length<12} type="submit">로그인</button><button disabled={busy||!username||password.length<12} type="button" onClick={()=>login(true)}>가상 계정 가입 후 로그인</button>
  </form>}
 </main>;
}
function Families(){
 const [families,setFamilies]=useState<Family[]>([]),[family,setFamily]=useState(''),[name,setName]=useState(''),[error,setError]=useState('');
 useEffect(()=>{const c=new AbortController();accountRequest('/families','GET',undefined,c.signal).then(v=>{if(!c.signal.aborted){setFamilies(v.families);setFamily(v.families[0]?.id??'');}}).catch(e=>{if(!c.signal.aborted)setError(e.message);});return()=>c.abort();},[]);
 async function add(){setError('');try{const v=await accountRequest('/families','POST',{name});setFamilies(f=>[...f,v]);setFamily(v.id);setName('');}catch(e){setError(e instanceof Error?e.message:'가족 추가 실패');}}
 return <section aria-label="내 계정 가족"><h2>내 가족 자료</h2>{error&&<p role="alert">{error}</p>}<label>가족 표시 이름<input value={name} onChange={e=>setName(e.target.value)} maxLength={60}/></label><button disabled={!name.trim()} onClick={add}>내 가족 추가</button>
  {families.length>0?<><label>저장할 가족<select value={family} onChange={e=>setFamily(e.target.value)}>{families.map(f=><option key={f.id} value={f.id}>{f.name}</option>)}</select></label><FamilyWorkspace key={family} family={families.find(f=>f.id===family)!}/></>:<p>가상의 가족 표시 이름을 추가해 주세요.</p>}
 </section>;
}
function FamilyWorkspace({family}:{family:Family}){
 const [file,setFile]=useState<File|null>(null),[date,setDate]=useState('2026-10-27'),[source,setSource]=useState<MedicationRecord['source_type']>('MEDICINE_BAG');
 const [epoch,setEpoch]=useState(0),[runs,setRuns]=useState<{id:string;created:string}[]>([]),[saved,setSaved]=useState<Saved|null>(null),[error,setError]=useState('');
 const [updating,setUpdating]=useState(false);
 const generation=useRef(0),abort=useRef<AbortController|null>(null);
 useEffect(()=>{void loadList();return()=>{generation.current++;abort.current?.abort();};},[]);
 async function loadList(){const id=++generation.current;abort.current?.abort();const c=new AbortController();abort.current=c;setSaved(null);setError('');try{const v=await accountRequest(`/families/${family.id}/runs`,'GET',undefined,c.signal);if(id===generation.current&&!c.signal.aborted)setRuns(v.runs);}catch(e){if(id===generation.current&&!c.signal.aborted)setError(e instanceof Error?e.message:'목록 조회 실패');}}
 async function detail(run:string){const id=++generation.current;abort.current?.abort();const c=new AbortController();abort.current=c;setSaved(null);setError('');try{const v=await accountRequest(`/families/${family.id}/runs/${run}`,'GET',undefined,c.signal);if(id===generation.current&&!c.signal.aborted){if(v.family_member_id!==family.id)throw new Error('저장 가족이 다릅니다.');setSaved(v);}}catch(e){if(id===generation.current&&!c.signal.aborted)setError(e instanceof Error?e.message:'자료 조회 실패');}}
 async function verify(record:string,choice:string){if(!saved)return;setUpdating(true);const run=saved.run_id;const id=++generation.current;abort.current?.abort();const c=new AbortController();abort.current=c;try{await accountRequest(`/families/${family.id}/runs/${run}/intake`,'PATCH',{record_id:record,choice},c.signal);if(id===generation.current&&!c.signal.aborted)await detail(run);}catch(e){if(id===generation.current&&!c.signal.aborted)setError(e instanceof Error?e.message:'복용 확인 저장 실패');}finally{setUpdating(false);}}
 const reset=()=>{setEpoch(e=>e+1);setSaved(null);};
 return <section aria-label="로그인 가족 작업"><h3>{family.name} · 사진 연결과 저장</h3>
  <label>현재 사진<input type="file" accept=".png,.jpg,.jpeg,.webp" onChange={e=>{setFile(e.target.files?.[0]??null);reset();}}/></label>
  <label>현재 기준일<input type="date" value={date} onChange={e=>{setDate(e.target.value);reset();}}/></label>
  <label>사진 자료 유형<select value={source} onChange={e=>{setSource(e.target.value as typeof source);reset();}}><option value="MEDICINE_BAG">약봉투</option><option value="PRESCRIPTION">처방전</option><option value="SUPPLEMENT">건강기능식품</option></select></label>
  <PhotoWorkflow key={epoch} uploaded account familyMemberId={family.id} familyLabel={family.name} sourceType={source} sourceLabel="가상 사진" recordDate={date} file={file}/>
  <h3>이 가족의 저장 목록</h3><button onClick={loadList}>저장 목록 새로고침</button>{error&&<p role="alert">{error}</p>}
  {runs.length===0&&<p>저장된 결과가 없습니다.</p>}{runs.map((r,i)=><button key={r.id} onClick={()=>detail(r.id)}>저장 결과 {i+1} · {r.created}</button>)}
  {saved&&<section aria-label="저장된 약 정보"><h3>저장된 약 정보 · {family.name}</h3>
   <details><summary>저장 원본·수정·정규화·후보 확인 구분</summary><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify({original:saved.result.original_results,edited:saved.result.edited_records,reviews:saved.reviews,normalized:saved.result.normalization_results},null,2)}</pre></details>
   {saved.result.reconciliation_result?.items.map((item,index)=>{const record=item.current_record??item.previous_record;const state=saved.intake_states.find(s=>s.medication_record_id===record!.record_id);const timeline=medicationTimeline({...item,id:`saved-${index}`});return <article className="card" key={record!.record_id}><h4>{productName(record)} · {labels[item.status]}</h4><p>이전: {timeline.previous.recordDate} · {timeline.previous.productStrength} · {timeline.previous.dosePerAdministration}</p><p>현재: {timeline.current.recordDate} · {timeline.current.productStrength} · {timeline.current.dosePerAdministration}</p><p>실제 복용: {state?intakeChoiceLabels[state.intake_status]:'잘 모르겠음'} · {state?verificationLabels[state.verification_status]:'확인 전'}</p>{Object.entries(intakeChoiceLabels).map(([choice,label])=><button disabled={updating} key={choice} onClick={()=>verify(record!.record_id,choice)}>{label} 저장</button>)}</article>;})}
  </section>}
 </section>;
}
