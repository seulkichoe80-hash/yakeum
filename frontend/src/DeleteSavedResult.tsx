import { useEffect, useRef, useState } from 'react';
type Props={kind:'사진'|'HIRA';family:string;created:string;run:string;busy:boolean;onConfirm:()=>void};
export function DeleteSavedResult({kind,family,created,run,busy,onConfirm}:Props){
 const [confirming,setConfirming]=useState(false);const cancel=useRef<HTMLButtonElement>(null),opener=useRef<HTMLButtonElement>(null);
 useEffect(()=>{if(confirming)cancel.current?.focus();},[confirming]);
 if(!confirming)return <button ref={opener} disabled={busy} onClick={()=>setConfirming(true)}>이 {kind} 저장 결과 삭제</button>;
 return <section className="notice" aria-label={`${kind} 삭제 확인`}>
  <strong>{family}의 {kind} 저장 결과를 삭제할까요?</strong><p>저장 시각: {created} · 자료 ID: <span style={{overflowWrap:'anywhere'}}>{run}</span></p>
  <p>이 저장 결과에 포함된 원본 정보·수정값·정규화·비교 또는 보류 결과와 연결된 복용 확인이 함께 삭제됩니다. 다른 저장 자료와 계정·가족은 유지합니다. 원본 파일은 서버에 보관하지 않습니다.</p>
  <p>화면에서 되돌릴 수 없습니다. 다른 결과가 참조하는 임시 후보와 기존 백업은 함께 삭제하지 않습니다.</p>
  <button ref={cancel} disabled={busy} onClick={()=>{setConfirming(false);queueMicrotask(()=>opener.current?.focus());}}>삭제 취소</button>
  <button disabled={busy} onClick={onConfirm}>이 {kind} 결과 삭제 확인</button>
 </section>;
}
