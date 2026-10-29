import { useEffect, useRef, useState } from 'react';
import { accountRequest } from './accountApi';

type ProbeStatus={response_version:'ADMIN_MFDS_PROBE_V1';state:'UNUSED'|'STARTED_OR_UNCERTAIN'|'FINISHED';consumed:boolean;started_at:string|null;result:unknown};
const base='/admin/mfds-probe';
function statusValue(value:unknown):ProbeStatus{
 const v=value as ProbeStatus;
 if(!v||v.response_version!=='ADMIN_MFDS_PROBE_V1'||!['UNUSED','STARTED_OR_UNCERTAIN','FINISHED'].includes(v.state)||typeof v.consumed!=='boolean'||v.consumed!==(v.state!=='UNUSED'))throw new Error('관리자 검증 상태를 확인할 수 없습니다.');
 return v;
}
export function AdminMfdsProbe(){
 const [available,setAvailable]=useState(false),[open,setOpen]=useState(false),[status,setStatus]=useState<ProbeStatus|null>(null);
 const [confirmed,setConfirmed]=useState(false),[running,setRunning]=useState(false),[message,setMessage]=useState('');
 const posted=useRef(false),active=useRef(false),generation=useRef(0);
 const reader=useRef<AbortController|null>(null),writer=useRef<AbortController|null>(null);
 async function read(initial=false){
  const id=++generation.current;reader.current?.abort();const c=new AbortController();reader.current=c;
  if(!initial){setStatus(null);setMessage('저장된 상태 확인 중… 외부 조회는 실행하지 않습니다.');}
  try{
   const value=statusValue(await accountRequest(base+'/status','GET',undefined,c.signal));
   if(!active.current||c.signal.aborted||id!==generation.current)return;
   setAvailable(true);setStatus(value);setMessage(value.state==='UNUSED'?'아직 사용하지 않았습니다.':value.state==='FINISHED'?'실행이 종료되었습니다. 저장된 결과만 표시합니다.':'실행이 시작됐거나 결과가 불명확합니다. 재전송하지 말고 상태만 확인하세요.');
  }catch(e){
   if(!active.current||c.signal.aborted||id!==generation.current)return;
   if(initial){setAvailable(false);return;}
   setStatus(null);setMessage(e instanceof Error?e.message:'상태를 확인하지 못했습니다. 다시 로그인하거나 관리자 설정을 확인하세요.');
  }
 }
 useEffect(()=>{active.current=true;void read(true);return()=>{active.current=false;generation.current++;reader.current?.abort();writer.current?.abort();};},[]);
 async function execute(){
  if(posted.current||!confirmed||!status||status.consumed)return;
  posted.current=true;const id=++generation.current;reader.current?.abort();
  const c=new AbortController();writer.current=c;setRunning(true);setStatus(null);
  setMessage('1회 실행 요청 중… 응답이 늦어도 다시 실행하지 마세요. 저장된 상태만 확인할 수 있습니다.');
  try{
   const value=statusValue(await accountRequest(base+'/execute','POST',{confirm:true},c.signal));
   if(active.current&&!c.signal.aborted&&id===generation.current){setStatus(value);setMessage('실행 상태와 안전한 결과입니다. 추가 호출은 하지 않습니다.');}
  }catch{
   if(active.current&&!c.signal.aborted&&id===generation.current)setMessage('실행 결과가 불명확합니다. 재전송하지 말고 저장된 상태를 확인하세요.');
  }finally{if(active.current)setRunning(false);}
 }
 if(!available)return null;
 return <section aria-label="관리자 식약처 검증">
  <button type="button" onClick={()=>setOpen(v=>!v)} aria-expanded={open}>식약처 관리자 검증 {open?'닫기':'열기'}</button>
  {open&&<section aria-label="식약처 관리자 검증 화면"><h2>식약처 연결 1회 검증</h2>
   <p>서버에서 지정한 관리자 전용입니다. 기존 사진·HIRA 가상 매칭은 유지됩니다.</p>
   <p>공개 제품명 ‘타이레놀’, 첫 페이지 3건을 최대 1회 조회합니다. 키를 입력하거나 표시하지 않습니다. 성분·함량 검증이나 앱 실제 매칭 완료를 뜻하지 않습니다.</p>
   <p>실패·연결 끊김·재시작에도 재실행하지 않습니다. 결과가 불명확하면 저장된 상태만 확인하세요.</p>
   <label><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>실제 외부 조회 최대 1회 실행에 동의합니다.</label>
   <button type="button" disabled={running||posted.current||!confirmed||!status||status.consumed} onClick={execute}>실제 조회 1회 실행</button>
   <button type="button" onClick={()=>void read()}>저장된 상태 확인 (외부 호출 없음)</button>
   <p role="status" aria-live="polite">{message}</p>
   {status&&<pre aria-label="안전한 진단 결과" style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify(status,null,2)}</pre>}
  </section>}
 </section>;
}
