export function MfdsLookupDiagnostics({mode,value}:{mode:string;value?:unknown}){
 if(mode!=='MFDS_LIVE')return null;
 const v=value as {response_version?:string;request_attempts?:number;queries?:{category?:string}[]}|undefined;
 return <section aria-label="식약처 조회 진단"><h4>실제 식약처 처리 출처·진단</h4>
  <p>실제 조회 경로 표시입니다. 제품 매칭 성공이나 복용 확인 완료를 뜻하지 않습니다.</p>
  {v?.response_version==='MFDS_LOOKUP_DIAGNOSTICS_V1'?<>
   <p>요청 시도: {v.request_attempts}회 · 오류/처리 분류: {v.queries?.map(q=>q.category??'미확인').join(', ')||'외부 조회 없음'}</p>
   <details><summary>안전한 조회 진단 요약</summary><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify(value,null,2)}</pre></details>
  </>:<p>이전 버전 결과에는 상세 진단 정보가 없습니다. 실패 원인은 미확인입니다. 진단을 얻기 위해 재조회하지 마세요.</p>}
 </section>;
}
