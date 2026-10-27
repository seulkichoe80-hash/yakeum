import { useEffect, useId, useReducer, useRef, useState } from 'react';
import type { MedicationRecord } from './types';
import { fileError } from './validation';
import './imageReview.css';
import { changedFields, demoLabels, draftFrom, draftIssues, extractionLabels, initialReviewState, mockExtraction, reviewReducer, type CandidateDraft, type CandidateReview, type DemoCase, type ExtractionResult, type ReviewState } from './imageReviewModel';

type Props = {familyMemberId:string;familyLabel:string;sourceType:MedicationRecord['source_type'];sourceLabel:string;recordDate:string;file:File|null;
 uploaded?:boolean;account?:boolean;gemini?:boolean;
 loadResults?:(scenario:DemoCase,signal:AbortSignal)=>Promise<ExtractionResult[]>;
 onReviewChange?:(state:ReviewState)=>void};
export function ImageReviewPanel(props:Props) {
 const panelId = useId();
 const [scenario,setScenario] = useState<DemoCase>('single');
 const [state,dispatch] = useReducer(reviewReducer,undefined,initialReviewState);
 const [preview,setPreview] = useState<string|null>(null);
 const [badImage,setBadImage] = useState(false);
 const timer = useRef<ReturnType<typeof setTimeout>|null>(null);
 const pending = useRef(false);
 const request = useRef(0);
 const controller = useRef<AbortController|null>(null);
 const resultHeading = useRef<HTMLHeadingElement>(null);
 const errorPanel = useRef<HTMLDivElement>(null);
 useEffect(()=>{
  if(!props.file) return;
  const url=URL.createObjectURL(props.file);setPreview(url);
  return ()=>URL.revokeObjectURL(url);
 },[props.file]);
 useEffect(()=>()=>{if(timer.current) clearTimeout(timer.current);controller.current?.abort();pending.current=false;request.current++;},[]);
 useEffect(()=>{props.onReviewChange?.(state);},[state,props.onReviewChange]);
 useEffect(()=>{if(state.phase==='ready') resultHeading.current?.focus();if(state.phase==='failed') errorPanel.current?.focus();},[state.phase]);
 function start() {
  if(pending.current) return;
  pending.current=true;
  const id=++request.current;
  dispatch({type:'start',requestId:id});
  if(props.loadResults) {
   controller.current=new AbortController();
   props.loadResults(scenario,controller.current.signal).then(results=>{
    if(request.current!==id||!pending.current) return;
    dispatch({type:'finish',requestId:id,results});pending.current=false;
   }).catch(error=>{
    if(request.current!==id||!pending.current) return;
    dispatch({type:'finish',requestId:id,results:[{status:'FAILED',record:null,warnings:[],errors:[{code:'AI_EXTRACTION_FAILED',message:error instanceof Error?error.message:'로컬 Mock 요청 실패',field:null}]}]});pending.current=false;
   });
   return;
  }
  timer.current=setTimeout(()=>{
   const invalidFile=props.file?fileError(props.file.name,props.file.size,false):null;
   const results=invalidFile?[{status:'FAILED' as const,record:null,warnings:[],errors:[{code:'INPUT_FILE_ERROR',message:invalidFile,field:null}]}]:mockExtraction(scenario,props.familyMemberId,props.sourceType,props.recordDate);
   dispatch({type:'finish',requestId:id,results});
   pending.current=false;timer.current=null;
  },650);
 }
 function cancel() {if(timer.current) clearTimeout(timer.current);controller.current?.abort();request.current++;timer.current=null;pending.current=false;dispatch({type:'reset'});}
 function edit(candidate:CandidateReview, patch:Partial<CandidateDraft>) { dispatch({type:'edit',key:candidate.key,draft:{...candidate.draft,...patch}}); }
 const completed=state.candidates.filter(c=>c.user_confirmed).length;
 return <div className="image-review">
  <h2>이미지 분석 결과 확인·수정</h2>
  {props.loadResults&&!props.uploaded&&<p className="info">LOCAL_MOCK 연결 · 서버의 가상 A JSON을 공통 adapter로 처리합니다. 이미지 업로드·실제 Gemini·식약처 호출은 없습니다.</p>}
  {props.gemini?<div className="info">Gemini 추출 후보 · 이미지가 외부로 전송될 수 있습니다. 모든 후보를 원본과 대조하고 확인하세요. 표시된 모델 신뢰도는 검증된 정확도가 아닙니다.</div>:props.uploaded?<div className="info">사진 업로드 연결 검사 · 선택 사진을 로컬 서버로 전송합니다. 후보는 이미지에서 인식한 값이 아닌 가짜 AI 응답입니다. {props.account?'외부 API 호출 없이 원본 후보는 개발용 로컬 DB에 보관합니다.':'외부 API·영구 저장은 없습니다.'}</div>:<div className="info">MOCK 시연 · 선택한 이미지에서 아래 값을 인식한 것이 아닙니다. 실제 AI 호출·전송·서버 저장은 하지 않습니다. 가상 예제로 검토 흐름을 확인하세요.</div>}
  <p>가족: <strong>{props.familyLabel}</strong> · 자료: {props.sourceLabel} · 기준일: {props.recordDate || '미선택'}</p>
  <details className="source-preview"><summary>원본 이미지 대조 {props.file ? '· 선택 파일' : '· 선택 사항'}</summary>
   {preview && !badImage ? <img src={preview} alt="사용자가 선택한 원본 이미지 대조용 미리보기" onError={()=>setBadImage(true)}/> : <p>{badImage ? '이미지를 표시할 수 없습니다. 다른 파일을 선택해 주세요.' : '위에서 이미지를 선택하면 미리 볼 수 있습니다. 개인정보 없는 가상 이미지를 사용하세요.'}</p>}
   {props.file && <p className="filename">선택 파일: {props.file.name} · {props.gemini?'추출 후보를 원본과 대조해 주세요.':'아래 후보는 이 파일과 무관한 가상 값입니다.'}</p>}
  </details>
  <div className="demo-controls">{!props.gemini&&<label>가상 추출 사례<select value={scenario} disabled={state.phase==='loading'} onChange={e=>{setScenario(e.target.value as DemoCase);dispatch({type:'reset'});}}>{(Object.keys(demoLabels) as DemoCase[]).map(key=><option key={key} value={key}>{demoLabels[key]}</option>)}</select></label>}
   <button className="primary" onClick={start} disabled={state.phase==='loading'||!props.recordDate}>{state.phase==='loading'?(props.gemini?'Gemini 요청 중…':'가상 분석 중…'):props.gemini?'Gemini로 사진 추출 요청':props.uploaded?'사진 업로드 후 가짜 후보 보기':'가상 추출 결과 보기'}</button>
  </div>
  {!props.recordDate&&<p role="alert" className="field-error">자료 기준일을 선택해 주세요.</p>}
  {state.phase==='loading' && <div role="status" className="info">{props.gemini?'Gemini 요청 중입니다. 최대 60초이며 취소해도 이미 전송된 요청/비용은 취소되지 않을 수 있습니다.':'가상 결과를 준비하고 있습니다. 실제 이미지 분석 요청은 없습니다.'} <button onClick={cancel}>{props.gemini?'Gemini 요청 화면 취소':'가상 분석 취소'}</button></div>}
  {state.phase==='failed' && <div ref={errorPanel} className="image-error" role="alert" tabIndex={-1}><h3>{props.gemini?'Gemini 추출을 완료하지 못했습니다':'가상 이미지 분석에 실패했습니다'}</h3><p>{state.error}</p><button onClick={start}>{props.gemini?'Gemini 요청 재시도 (추가 호출)':'같은 사례 재시도'}</button><p>{props.gemini?'실패 또는 시간 초과일 수 있습니다. 서버 설정·호출 한도와 원본을 확인하세요. 자동 재시도하지 않습니다.':'성공 흐름은 위 사례를 정상 제품으로 바꿔 확인할 수 있습니다.'}</p></div>}
  {state.phase==='ready' && <>
   <h3 ref={resultHeading} tabIndex={-1}>약품 후보 {state.candidates.length}개 · 화면 확인 완료 {completed}개</h3>
   <p className="info">이곳의 확인은 <strong>추출 내용의 대조</strong>입니다. 실제 복용 여부(TAKING/NOT_TAKING/UNKNOWN), 비교 판정, 정규화 결과를 변경하지 않습니다. 모르는 값은 추측하지 말고 비워 두거나 확인을 보류하세요.</p>
   {state.candidates.map((candidate,index)=>{
    const issues=draftIssues(candidate.draft), original=draftFrom(candidate.original), modified=changedFields(candidate);
    const prefix=`${panelId}-${candidate.key}`;
    const field=(key:keyof Omit<CandidateDraft,'ingredients'>,label:string,numeric=false)=><label className="review-field">{label}<input aria-label={label} value={candidate.draft[key]} inputMode={numeric?'decimal':undefined} aria-invalid={!!issues[key]} aria-describedby={`${prefix}-${key}-original${issues[key]?` ${prefix}-${key}-error`:''}`} onChange={e=>edit(candidate,{[key]:e.target.value})}/><small id={`${prefix}-${key}-original`}>AI 추출값: {original[key]===''?'미확인':original[key]}{original[key]!==candidate.draft[key]?' · 사용자 수정':''}</small>{issues[key]&&<span id={`${prefix}-${key}-error`} className="field-error">{issues[key]}</span>}</label>;
    return <form key={candidate.key} className="candidate-card" noValidate onSubmit={e=>{e.preventDefault();dispatch({type:'confirm',key:candidate.key});if(Object.keys(issues).length)e.currentTarget.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus();else if(!candidate.acknowledged)e.currentTarget.querySelector<HTMLInputElement>('input[type="checkbox"]')?.focus();}} aria-label={`약품 후보 ${index+1}`}>
     <div className="candidate-heading"><h3>후보 {index+1} · {candidate.draft.product||'제품명 미확인'}</h3><span className="badge">{extractionLabels[candidate.original.status]}</span></div>
     <p>{props.gemini?'추출 출처':'가상 출처'}: {candidate.original.record?.source_record_id ?? `가상 문서의 후보 ${index+1} · 원본 record 없음`} · 신뢰도: {candidate.original.record?.confidence ?? '미확인'}</p>
     {candidate.original.warnings.length>0&&<ul className="candidate-warnings">{candidate.original.warnings.map((w,n)=><li key={n}>{w.message}</li>)}</ul>}
     {candidate.original.errors.length>0&&<ul className="field-error" role="alert">{candidate.original.errors.map((error,n)=><li key={n}>{error.message}</li>)}</ul>}
     {!candidate.original.record&&<p className="info">원본 record가 없는 후보입니다. 아래 입력은 화면용 임시 초안이며, 공통 MedicationRecord를 생성하거나 서버로 보내지 않습니다.</p>}
     {field('product','제품명')}
     <fieldset><legend>성분별 제품 함량</legend>
      {candidate.draft.ingredients.length===0&&<p>확인된 성분 정보가 없습니다. 알 수 없는 경우 빈 값으로 유지합니다.</p>}
      {candidate.draft.ingredients.map((ingredient,n)=><div className="ingredient-editor" key={n}>
       {(['name','strength','unit'] as const).map((key)=>{
        const issueKey=`ingredient-${n}-${key}`;
        const label=`성분 ${n+1} ${key==='name'?'이름':key==='strength'?'제품 함량':'함량 단위'}`;
        const originalIngredient=ingredient.originalIndex === null ? undefined : original.ingredients[ingredient.originalIndex];
        return <label className="review-field" key={key}>{label}
         <input aria-label={label} value={ingredient[key]} inputMode={key==='strength'?'decimal':undefined} aria-invalid={!!issues[issueKey]} aria-describedby={`${prefix}-${issueKey}-original${issues[issueKey]?` ${prefix}-${issueKey}-error`:''}`} onChange={e=>edit(candidate,{ingredients:candidate.draft.ingredients.map((row,i)=>i===n?{...row,[key]:e.target.value}:row)})}/>
         <small id={`${prefix}-${issueKey}-original`}>AI 추출값: {originalIngredient?.[key] || '미확인'}{originalIngredient?.[key]!==ingredient[key]?' · 사용자 수정':''}</small>
         {issues[issueKey]&&<span id={`${prefix}-${issueKey}-error`} className="field-error">{issues[issueKey]}</span>}
        </label>;
       })}
       <button type="button" onClick={()=>edit(candidate,{ingredients:candidate.draft.ingredients.filter((_,i)=>i!==n)})}>성분 {n+1} 삭제</button>
      </div>)}
      <button type="button" onClick={()=>edit(candidate,{ingredients:[...candidate.draft.ingredients,{name:'',strength:'',unit:'',originalIndex:null}]})}>성분 추가</button>
     </fieldset>
     <div className="review-grid">{field('dose','1회 투약량',true)}{field('doseUnit','투약 단위 (정·캡슐 등)')}{field('perDay','하루 투여 횟수',true)}{field('duration','투약일수',true)}</div>
     {field('directions','원본 복용법 문구')}
     <p>사용자 수정: {modified.length}개 항목 · 공란은 미확인 값으로 유지됩니다.</p>
     <label className="check"><input type="checkbox" checked={candidate.acknowledged} onChange={e=>dispatch({type:'acknowledge',key:candidate.key,value:e.target.checked})}/>후보 {index+1}의 추출 내용과 수정값을 원본과 대조했습니다.</label>
     {candidate.attempted&&!candidate.user_confirmed&&<p role="alert" className="field-error">표시된 입력 오류를 확인하고 원본 대조에 체크해 주세요.</p>}
     <div className="candidate-actions"><button className="primary" type="submit" disabled={candidate.user_confirmed||candidate.original.status==='FAILED'}>추출 내용 확인 완료 (로컬)</button><button type="button" onClick={()=>dispatch({type:'defer',key:candidate.key})}>확인 보류</button><button type="button" onClick={()=>dispatch({type:'restore',key:candidate.key})}>AI 추출값으로 되돌리기</button></div>
     <p role="status" className="confirmation-state">{candidate.user_confirmed?'화면 확인 완료 · 로컬 user_confirmed=true':candidate.deferred?'확인 보류 · user_confirmed=false':'확인 전 · user_confirmed=false'}</p>
     <small>원본 추출 결과의 user_confirmed=false는 보존됩니다. 다시 수정하면 화면 확인도 초기화됩니다. 서버 저장·정규화·실제 복용상태에는 반영되지 않습니다.</small>
    </form>;
   })}
   {completed===state.candidates.length&&<div role="status" className="info">모든 후보의 추출 내용을 화면에서 확인했습니다. 실제 복용 여부 확인 또는 서버 저장 완료를 뜻하지 않습니다.</div>}
  </>}
 </div>;
}
