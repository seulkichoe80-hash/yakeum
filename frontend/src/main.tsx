import React, { useEffect, useReducer, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
 initialMembers, mockResult, labels, statuses, primaryMemberId, productName,
 ingredientText, strengthText, toItems, type Status, type Item, type Member,
} from './domain';
import { requestHiraComparison } from './api';
import {
 getCurrentIntakeState, initialCurrentIntakeState, intakeChoiceLabels,
 replaceFamilyIntakeStates, verificationLabels, verifyCurrentIntake,
 type CurrentIntakeStore, type IntakeChoice,
} from './currentIntakeUi';
import { initialIntegrationState, integrationReducer } from './integrationState';
import {
 groupNormalizationAttention, localMockNotice, normalizationLabels, reconciliationDescriptions,
} from './presentation';
import {
 initialResultViewState, mockItemsForFamily, resultViewReducer,
} from './resultView';
import { medicationTimeline } from './timeline';
import { fileError, reviewError } from './validation';
import './style.css';

function App() {
 const [members, setMembers] = useState(initialMembers);
 const [memberId, setMemberId] = useState(primaryMemberId);
 const member = members.find(candidate => candidate.id === memberId)!;
 const [integration, dispatchIntegration] = useReducer(
  integrationReducer,
  initialIntegrationState(primaryMemberId),
 );
 const [resultView, dispatchResultView] = useReducer(
  resultViewReducer,
  initialResultViewState(primaryMemberId),
 );
 const [page, setPage] = useState('overview');
 const [filter, setFilter] = useState<Status | 'ALL'>('ALL');
 const [query, setQuery] = useState('');
 const [selected, setSelected] = useState<Item | null>(null);
 const [notice, setNotice] = useState('');
 const [source, setSource] = useState('심평원 Excel');
 const [previousFile, setPreviousFile] = useState<File | null>(null);
 const [currentFile, setCurrentFile] = useState<File | null>(null);
 const [file, setFile] = useState<File | null>(null);
 const [date, setDate] = useState('2026-10-08');
 const [uploadState, setUploadState] = useState<'idle' | 'review' | 'done'>('idle');
 const [product, setProduct] = useState('');
 const [strength, setStrength] = useState('');
 const [unit, setUnit] = useState('');
 const [confirmed, setConfirmed] = useState(false);
 const [name, setName] = useState('');
 const [relation, setRelation] = useState('');
 const [intakeStore, setIntakeStore] = useState<CurrentIntakeStore>({});
 const [tab, setTab] = useState('기본정보');
 const [month, setMonth] = useState('2026-09');
 const dialogRef = useRef<HTMLElement>(null);
 const openerRef = useRef<HTMLElement | null>(null);
 const activeMemberRef = useRef(memberId);

 const allowed = member.consent && member.approved;
 const backendResponse = resultView.mode === 'BACKEND' && integration.phase === 'success'
  ? integration.response
  : null;
 const backendItems = backendResponse ? toItems(backendResponse.reconciliation_result) : null;
 const mockItems = resultView.mode === 'MOCK' ? mockItemsForFamily(mockResult.items, memberId) : null;
 const items = backendItems ?? mockItems ?? [];
 const isBackend = resultView.mode === 'BACKEND' && backendItems !== null;
 const isMock = resultView.mode === 'MOCK';
 const pending = items.filter(item => item.status === 'NEEDS_CONFIRMATION');
 const visible = items.filter(item =>
  (filter === 'ALL' || item.status === filter)
  && productName(item.current_record ?? item.previous_record).includes(query),
 );
 const reviewResults = backendResponse
  ? [...backendResponse.review_results.previous, ...backendResponse.review_results.current]
  : [];
 const normalizationGroups = backendResponse
  ? groupNormalizationAttention(backendResponse.accepted_results)
  : [];
 const normalizationAttentionCount = normalizationGroups.reduce(
  (count, group) => count + group.results.length,
  0,
 );
 const inputError = reviewError(product, strength, unit);
 const selectedTimeline = selected ? medicationTimeline(selected) : null;

 function resetUpload() {
  setUploadState('idle');
  setConfirmed(false);
  setProduct('');
  setStrength('');
  setUnit('');
  setNotice('');
 }

 function switchMember(id: string) {
  activeMemberRef.current = id;
  setMemberId(id);
  dispatchIntegration({ type: 'memberChanged', memberId: id });
  dispatchResultView({ type: 'memberChanged', memberId: id });
  setSelected(null);
  setPreviousFile(null);
  setCurrentFile(null);
  setFile(null);
  resetUpload();
  setQuery('');
  setFilter('ALL');
  setMonth('2026-09');
 }

 function openDetails(item: Item, detailTab: string) {
  openerRef.current = document.activeElement as HTMLElement;
  setSelected(item);
  setTab(detailTab);
 }

 useEffect(() => {
  if (!selected || !allowed) return;
  const oldOverflow = document.body.style.overflow;
  const background = Array.from(document.querySelectorAll<HTMLElement>('aside, main'))
   .map(element => ({ element, wasInert: element.inert }));
  background.forEach(({ element }) => { element.inert = true; });
  document.body.style.overflow = 'hidden';
  dialogRef.current?.querySelector<HTMLButtonElement>('button')?.focus();
  const onKey = (event: KeyboardEvent) => {
   if (event.key === 'Escape') {
    event.preventDefault();
    setSelected(null);
    return;
   }
   if (event.key !== 'Tab') return;
   const controls = Array.from(
    dialogRef.current?.querySelectorAll<HTMLElement>(
     'button, a[href], input, select, textarea, [tabindex="0"]',
    ) ?? [],
   ).filter(element => !element.hasAttribute('disabled') && element.getClientRects().length > 0);
   const first = controls[0];
   const last = controls[controls.length - 1];
   if (!first) {
    event.preventDefault();
   } else if (event.shiftKey && (document.activeElement === first || !dialogRef.current?.contains(document.activeElement))) {
    event.preventDefault();
    last.focus();
   } else if (!event.shiftKey && (document.activeElement === last || !dialogRef.current?.contains(document.activeElement))) {
    event.preventDefault();
    first.focus();
   }
  };
  document.addEventListener('keydown', onKey);
  return () => {
   document.removeEventListener('keydown', onKey);
   document.body.style.overflow = oldOverflow;
   background.forEach(({ element, wasInert }) => { element.inert = wasInert; });
   if (openerRef.current?.isConnected) openerRef.current.focus({ preventScroll: true });
  };
 }, [selected, allowed]);

 function patchMember(patch: Partial<Member>) {
  setMembers(current => current.map(candidate =>
   candidate.id === memberId ? { ...candidate, ...patch } : candidate,
  ));
 }

 async function analyzeHira() {
  if (!allowed) {
   setNotice('화면 시연용 동의와 가족 열람 승인을 먼저 확인해 주세요. 서버 권한 인증은 아직 구현되지 않았습니다.');
   return;
  }
  if (!previousFile || !currentFile) {
   setNotice('이전 XLSX와 현재 XLSX를 모두 선택해 주세요.');
   return;
  }
  const previousError = fileError(previousFile.name, previousFile.size, true);
  const currentError = fileError(currentFile.name, currentFile.size, true);
  if (previousError || currentError) {
   setNotice(previousError ?? currentError ?? '파일을 확인해 주세요.');
   return;
  }

  const requestMemberId = memberId;
  dispatchIntegration({ type: 'started', memberId: requestMemberId });
  dispatchResultView({ type: 'backendStarted', memberId: requestMemberId });
  setNotice('가상 XLSX를 Backend에서 실제 처리하고 있습니다. 외부 식약처 API는 호출하지 않습니다.');
  try {
   const response = await requestHiraComparison({
    familyMemberId: requestMemberId,
    previousFile,
    currentFile,
   });
   if (activeMemberRef.current !== requestMemberId) return;
   setIntakeStore(current => replaceFamilyIntakeStates(
    current,
    requestMemberId,
    toItems(response.reconciliation_result),
    response.current_intake_states,
   ));
   dispatchIntegration({ type: 'succeeded', memberId: requestMemberId, response });
   dispatchResultView({ type: 'backendSucceeded', memberId: requestMemberId });
   setFilter('ALL');
   setQuery('');
   setPage('overview');
   setNotice('가상 XLSX 처리 완료: deterministic parser · D 비교 · MFDS LOCAL MOCK 결과입니다.');
  } catch (error) {
   if (activeMemberRef.current !== requestMemberId) return;
   const message = error instanceof Error ? error.message : '자료 처리 요청에 실패했습니다.';
   dispatchIntegration({ type: 'failed', memberId: requestMemberId, error: message });
   setNotice(message);
  }
 }

 function showMock() {
  const itemsForMember = mockItemsForFamily(mockResult.items, memberId);
  dispatchIntegration({ type: 'memberChanged', memberId });
  dispatchResultView({ type: 'mockSelected', memberId });
  setIntakeStore(current => replaceFamilyIntakeStates(current, memberId, itemsForMember));
  setFilter('ALL');
  setQuery('');
  setMonth('2026-09');
  setNotice('사용자가 명시적으로 선택한 가상 고정 Mock입니다. 실제 자료가 저장되거나 복구된 것이 아닙니다.');
 }

 function registerDemo() {
  if (!allowed) {
   setNotice('먼저 화면 시연용 동의와 가족 열람 승인을 완료해 주세요.');
   return;
  }
  if (!file || !date) {
   setNotice('파일과 자료 기준일을 선택해 주세요.');
   return;
  }
  const error = fileError(file.name, file.size, false);
  if (error) {
   setUploadState('idle');
   setConfirmed(false);
   setNotice(error);
   return;
  }
  setProduct('');
  setStrength('');
  setUnit('');
  setConfirmed(false);
  setUploadState('review');
  setNotice('비정형 자료는 아직 Backend로 전송되지 않는 UI 데모입니다.');
 }

 function confirmCurrentIntake(item: Item, value: IntakeChoice) {
  const recordId = item.previous_record?.record_id ?? item.current_record?.record_id;
  if (!recordId) return;
  setIntakeStore(current => {
   const withInitial = getCurrentIntakeState(current, memberId, recordId)
    ? current
    : {
      ...current,
      [memberId]: {
       ...current[memberId],
       [recordId]: initialCurrentIntakeState(memberId, recordId),
      },
     };
   return verifyCurrentIntake(withInitial, memberId, recordId, value);
  });
  setNotice('현재 브라우저에서만 유지되며 저장되지 않습니다. ReconciliationResult는 변경되지 않았습니다.');
 }

 const modeLabel = isBackend
  ? 'BACKEND · 가상 XLSX · MFDS LOCAL MOCK'
  : isMock
   ? 'MOCK · 명시적 미리보기'
   : '결과 없음 · 재분석 필요';

 return <div className="shell">
  <aside>
   <a className="logo" href="#" onClick={() => setPage('overview')}><span>＋</span> 약이음</a>
   <p className="subtitle">가족을 잇는 복용정보</p>
   <nav>{[
    ['overview', '◫', '가족 대시보드'],
    ['upload', '↥', '자료 등록'],
    ['inbox', '✓', '확인함'],
    ['family', '♧', '가족 · 동의 관리'],
   ].map(([key, icon, text]) =>
    <button key={key} className={page === key ? 'active' : ''} onClick={() => {
     setPage(key);
     setNotice('');
    }}>{icon}　{text}{key === 'inbox' && allowed && pending.length > 0 && <b>{pending.length}</b>}</button>,
   )}</nav>
   <div className="aside-bottom">함께 확인하고,<br />더 정확하게 기록해요.<small>복용정보 정리 및 상담 보조 서비스</small></div>
  </aside>
  <main>
   <header>
    <div className="breadcrumb">우리 가족 / {page === 'overview' ? '대시보드' : page === 'upload' ? '자료 등록' : page === 'inbox' ? '확인함' : '가족 관리'}</div>
    <span className={'demo ' + (isBackend ? 'backend-mode' : isMock ? 'mock-mode' : 'empty-mode')}>{modeLabel}</span>
   </header>
   <div className="heading">
    <div>
     <p className="eyebrow">FAMILY MEDICATION RECORD</p>
     <h1>{page === 'overview' ? '우리 가족 복용정보' : page === 'upload' ? '새 자료 등록' : page === 'inbox' ? '함께 확인할 정보' : '가족과 동의 관리'}</h1>
     <p>흩어진 기록을 모아, 지난 기록과의 변화를 확인하세요.</p>
    </div>
    <label className="member-select">가족 구성원
     <select value={memberId} onChange={event => switchMember(event.target.value)}>
      {members.map(candidate =>
       <option key={candidate.id} value={candidate.id}>{candidate.relationship} · {candidate.name}</option>,
      )}
     </select>
    </label>
   </div>
   <div className="info">
    {isBackend
     ? `업로드한 가상 파일을 실제로 파싱·비교했습니다. ${localMockNotice} 결과는 저장되지 않습니다.`
     : isMock
      ? '사용자가 명시적으로 선택한 가상 고정 Mock입니다. 실제 업로드 결과나 저장된 자료가 아닙니다.'
      : '이 가족에게 표시할 비교 결과가 없습니다. 자료를 다시 분석하거나 가상 Mock 보기를 직접 선택해 주세요.'}
    {' '}표시된 변화는 복용 변경 지시가 아닙니다.
   </div>
   {notice && <div className="notice" role="status">{notice}</div>}
   {!allowed && page !== 'family'
    ? <section className="card empty">
      <h2>화면 시연용 동의와 승인이 필요해요</h2>
      <p>이 체크는 Backend 인증이나 실제 접근권한 검증이 아닙니다.</p>
      <button className="primary" onClick={() => setPage('family')}>동의 관리 열기</button>
     </section>
    : <>
     {page === 'overview' && (resultView.mode === 'EMPTY' ? <section className="card empty result-empty">
      <h2>표시할 비교 결과가 없습니다</h2>
      <p>가족을 전환하면 이전 업로드 결과는 초기화됩니다. 자료를 다시 분석하거나 가상 Mock을 명시적으로 선택해 주세요.</p>
      <div className="empty-actions">
       <button className="primary" onClick={() => setPage('upload')}>자료 분석하기</button>
       <button onClick={showMock}>가상 Mock 보기</button>
      </div>
      <small>실제 자료가 저장되거나 복구된 것처럼 표시하지 않습니다.</small>
     </section> : <>
      <div className="stats">{statuses.map(status =>
       <button key={status} className={'stat ' + status + (filter === status ? ' chosen' : '')} onClick={() => setFilter(filter === status ? 'ALL' : status)}>
        <span>{labels[status]}</span>
        <strong>{items.filter(item => item.status === status).length}<small>건</small></strong>
         <p>{reconciliationDescriptions[status]}</p>
       </button>,
      )}</div>
      <section className="card timeline">
       <div>
        <h2>복용정보 타임라인</h2>
        <p>{isBackend ? '사용자가 명시한 이전 XLSX → 현재 XLSX · D 엔진 결과' : '기준 자료: 2026년 8월 → 9월 · D 엔진 결과 Mock'}</p>
       </div>
       {!isBackend && <div className="months">{['2026-03', '2026-08', '2026-09'].map(value =>
        <button className={month === value ? 'current' : ''} key={value} onClick={() => setMonth(value)}>{value.slice(5)}월<span>●</span></button>,
       )}</div>}
      </section>
      {reviewResults.length > 0 && <section className="card processing-errors" role="alert">
       <h2>자료 처리 오류 {reviewResults.length}건</h2>
       <p>파일 또는 행을 처리하지 못한 결과입니다. 최신 자료 미확인 상태와는 다릅니다.</p>
       {reviewResults.map((result, index) =>
        <div className="issue" key={'failed-' + index}>
          <strong>{normalizationLabels.FAILED}</strong>
          <span>
           {[...result.errors, ...result.warnings].map(error => error.message).join(' · ') || '처리할 수 없는 행입니다.'}
           <small className="technical-status">기술 상태: FAILED</small>
          </span>
        </div>,
       )}
      </section>}
      {normalizationAttentionCount > 0 && <section className="card normalization-warning">
       <h2>제품 정보 정규화 확인 필요 {normalizationAttentionCount}건</h2>
       <p>원본 기록은 유지됩니다. 정규화 상태는 의약품 안전성 판단을 의미하지 않습니다. {localMockNotice}</p>
       {normalizationGroups.map(group => <details className="normalization-group" key={group.source}>
        <summary>{group.title}<strong>{group.results.length}건</strong></summary>
        {group.results.map((result, index) =>
         <div className="issue" key={`${group.source}-normalization-${index}`}>
           <strong>{normalizationLabels[result.status]}</strong>
           <span>
            {productName(result.record)} · {result.warnings.map(warning => warning.message).join(' · ') || normalizationLabels[result.status]}
            <small className="technical-status">기술 상태: {result.status}</small>
           </span>
         </div>,
        )}
       </details>)}
      </section>}
      {!isBackend && month !== '2026-09'
       ? <section className="card empty">
         <h2>{month} 기록 미제공</h2>
         <p>이번 Mock에는 9월 비교 결과와 개별 항목의 8월 이전 기록이 포함되어 있습니다.</p>
         <button onClick={() => setMonth('2026-09')}>9월 보기</button>
        </section>
       : <section className="card">
         <div className="section-heading">
          <div>
           <h2>{member.relationship}의 기록 비교</h2>
           <p>현재 자료 {items.filter(item => item.current_record).length}건 · 확인 필요 {pending.length}건</p>
          </div>
          <button className="primary" onClick={() => setPage('upload')}>＋ 자료 등록</button>
         </div>
         <div className="toolbar">
          <label>제품 검색 <input value={query} onChange={event => setQuery(event.target.value)} placeholder="제품명으로 검색" /></label>
          <select aria-label="변경 상태 필터" value={filter} onChange={event => setFilter(event.target.value as Status | 'ALL')}>
           <option value="ALL">전체 상태</option>
           {statuses.map(status => <option key={status} value={status}>{labels[status]}</option>)}
          </select>
         </div>
         <div className="records">
          {visible.map(item =>
           <button key={item.id} className="record" onClick={() => openDetails(item, '기본정보')}>
            <span className="pill-icon">◇</span>
            <span className="record-name">
             <strong>{productName(item.current_record ?? item.previous_record)}</strong>
             <small>{ingredientText(item.current_record ?? item.previous_record)} · {strengthText(item.current_record ?? item.previous_record)}</small>
             <small>{(item.current_record ?? item.previous_record)?.user_confirmed ? '사용자 확인됨' : '사용자 미확정 후보'}</small>
            </span>
            <span className={'badge ' + item.status}>{labels[item.status]}</span>
            <span className="record-date">{item.current_record ? item.current_record.record_date : '최신 자료에서 미확인'}</span>
            <span>›</span>
           </button>,
          )}
          {visible.length === 0 && <p className="empty">{isBackend ? '처리된 비교 결과가 없습니다.' : '조건에 맞는 기록이 없습니다.'}</p>}
         </div>
        </section>}
     </>)}
     {page === 'upload' && <section className="card form">
      <h2>자료를 등록할 가족과 파일 역할을 확인해 주세요</h2>
      <p>HIRA 비교에서는 사용자가 이전/현재 파일을 직접 구분하며 Backend가 날짜로 역할을 바꾸지 않습니다.</p>
      <label>자료 유형
       <select value={source} onChange={event => {
        setSource(event.target.value);
        setPreviousFile(null);
        setCurrentFile(null);
        setFile(null);
        resetUpload();
       }}>
        {['심평원 Excel', '약봉투 사진', '처방전 사진', '건강기능식품 사진'].map(value => <option key={value}>{value}</option>)}
       </select>
      </label>
      {source === '심평원 Excel' ? <>
       <div className="file-pair">
        <label className="dropzone">이전 자료
         <strong>{previousFile?.name ?? '이전 XLSX 선택'}</strong>
         <span>XLSX만 지원 · 최대 10MB</span>
         <input type="file" accept=".xlsx" onChange={event => setPreviousFile(event.target.files?.[0] ?? null)} />
        </label>
        <label className="dropzone">현재 자료
         <strong>{currentFile?.name ?? '현재 XLSX 선택'}</strong>
         <span>XLSX만 지원 · 최대 10MB</span>
         <input type="file" accept=".xlsx" onChange={event => setCurrentFile(event.target.files?.[0] ?? null)} />
        </label>
       </div>
       <button className="primary" disabled={integration.phase === 'loading'} onClick={analyzeHira}>
        {integration.phase === 'loading' ? 'Backend 처리 중…' : '가상 XLSX 분석 요청'}
       </button>
       {integration.phase === 'loading' && <div className="loading" role="status">파일을 deterministic parser와 D 엔진으로 처리하고 있습니다.</div>}
       {integration.phase === 'error' && <div className="error-panel" role="alert">
        <strong>자료 처리에 실패했습니다.</strong>
        <p>{integration.error}</p>
        <button onClick={analyzeHira}>같은 파일로 재시도</button>
       </div>}
      </> : <>
       <div className="notice inline-notice">비정형 자료 Backend는 아직 연결되지 않았습니다. 아래 흐름은 저장되지 않는 UI 데모입니다.</div>
       <label>자료 기준일<input type="date" value={date} onChange={event => {
        setDate(event.target.value);
        resetUpload();
       }} /></label>
       <label className="dropzone">↥
        <strong>{file?.name ?? '가상 이미지 파일 선택'}</strong>
        <span>JPG, PNG, WEBP · 최대 10MB</span>
        <input key={`${memberId}:${source}`} type="file" accept=".jpg,.jpeg,.png,.webp" onChange={event => {
         setFile(event.target.files?.[0] ?? null);
         resetUpload();
        }} />
       </label>
       <button className="primary" onClick={registerDemo}>확인 화면으로 이동 (데모)</button>
       {uploadState === 'review' && <div className="review">
        <h2>추출 결과 수정·확정</h2>
        <p>실제 인식 결과가 없으므로 확인할 값을 직접 입력하세요. 서버로 전송하거나 저장하지 않습니다.</p>
        <label>제품명<input value={product} onChange={event => setProduct(event.target.value)} /></label>
        <div className="row">
         <label>함량 (선택)<input type="text" inputMode="decimal" value={strength} aria-describedby="review-error" onChange={event => setStrength(event.target.value)} /></label>
         <label>단위 (선택)<input aria-describedby="review-error" value={unit} onChange={event => setUnit(event.target.value)} placeholder="예: mg" /></label>
        </div>
        <p id="review-error" className="field-error" role="status">{(product || strength || unit) && inputError}</p>
        <label className="check"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} />원본 자료와 입력 내용을 대조했습니다.</label>
        <button className="primary" disabled={!confirmed || inputError !== null} onClick={() => {
         setUploadState('done');
         setNotice('사용자 확정 UI 데모 완료. 실제 저장·정규화·비교는 실행되지 않았습니다.');
        }}>입력 내용 확정 (데모)</button>
       </div>}
       {uploadState === 'done' && <div className="info">{member.name} · {product} · {date} 입력을 화면 메모리에서만 확인했습니다.</div>}
      </>}
     </section>}
     {page === 'inbox' && <section className="card">
      <h2>최신 자료에서 확인되지 않은 항목</h2>
       <p>자료에서 보이지 않는다는 이유만으로 복용 중단으로 처리하지 않습니다.</p>
       <div className="browser-only-notice">현재 브라우저에서만 유지되며 저장되지 않습니다. 새로고침하면 초기화됩니다.</div>
      {pending.map(item => {
       const record = item.previous_record ?? item.current_record;
        const currentState = getCurrentIntakeState(intakeStore, memberId, record?.record_id ?? null)
         ?? (record ? initialCurrentIntakeState(memberId, record.record_id) : undefined);
       return <div className="pending" key={item.id}>
        <div>
         <strong>{productName(item.previous_record)}</strong>
          <p>이전 기록 기준일: {item.previous_record?.record_date ?? '미확인'}</p>
          <p>현재 자료에서 확인되지 않았습니다. 현재도 복용하고 있나요?</p>
          {currentState && <small className="intake-state">
           현재 응답: {intakeChoiceLabels[currentState.intake_status]} · {verificationLabels[currentState.verification_status]}
          </small>}
        </div>
        <button onClick={() => openDetails(item, '변경 이력')}>기록 살펴보기</button>
        <div className="confirmation-buttons">
          {(['TAKING', 'NOT_TAKING', 'UNKNOWN'] as IntakeChoice[]).map(choice =>
           <button
            key={choice}
            aria-pressed={currentState?.verification_status === 'USER_VERIFIED' && currentState.intake_status === choice}
            className={currentState?.verification_status === 'USER_VERIFIED' && currentState.intake_status === choice ? 'selected' : ''}
            onClick={() => confirmCurrentIntake(item, choice)}
           >{intakeChoiceLabels[choice]}</button>,
          )}
        </div>
       </div>;
      })}
      {pending.length === 0 && <div className="empty">지금 확인할 항목이 없습니다.</div>}
     </section>}
     {page === 'family' && <section className="card form">
      <h2>{member.name}님의 정보 접근</h2>
      <p>아래 체크는 UI 시연용입니다. 실제 동의·승인 및 접근권한은 서버에서 검증하지 않습니다.</p>
      <label className="check"><input type="checkbox" checked={member.consent} onChange={event => patchMember({ consent: event.target.checked })} />건강정보 수집·처리 동의 (데모)</label>
      <label className="check"><input type="checkbox" checked={member.approved} onChange={event => patchMember({ approved: event.target.checked })} />가족 열람 승인 (데모)</label>
      <hr />
      <h2>가족 구성원 추가</h2>
      <label>이름<input value={name} onChange={event => setName(event.target.value)} /></label>
      <label>관계<input value={relation} onChange={event => setRelation(event.target.value)} placeholder="예: 본인, 아버지" /></label>
      <button className="primary" disabled={!name.trim() || !relation.trim()} onClick={() => {
       const id = crypto.randomUUID();
       setMembers([...members, { id, name: name.trim(), relationship: relation.trim(), consent: false, approved: false }]);
       switchMember(id);
       setName('');
       setRelation('');
      }}>가족 추가 (데모)</button>
     </section>}
    </>}
   <footer>약이음은 복용정보를 정리합니다. 진단·처방·복용량 변경·복용 중단을 안내하지 않습니다.<br />업로드 파일과 결과는 이 로컬 PoC에서 영구 저장하지 않습니다.</footer>
  </main>
  {selected && allowed && <div className="overlay" onClick={() => setSelected(null)}>
   <section ref={dialogRef} className="detail" role="dialog" aria-modal="true" aria-label="복용정보 상세" onClick={event => event.stopPropagation()}>
    <div className="section-heading">
     <h2>{productName(selected.current_record ?? selected.previous_record)}</h2>
     <button autoFocus onClick={() => setSelected(null)} aria-label="상세 닫기">닫기 ×</button>
    </div>
    <span className={'badge ' + selected.status}>{labels[selected.status]}</span>
    <div className="tabs">{['기본정보', '성분·함량', '공식 근거', '변경 이력'].map(value =>
     <button className={tab === value ? 'active' : ''} key={value} onClick={() => setTab(value)}>{value}</button>,
    )}</div>
    {tab === '기본정보' && <dl>
     <dt>자료 기준일</dt><dd>{(selected.current_record ?? selected.previous_record)?.record_date}</dd>
     <dt>복용법</dt><dd>{(selected.current_record ?? selected.previous_record)?.dosage_text_raw ?? '미확인'}</dd>
     <dt>공식 제품 코드</dt><dd>{(selected.current_record ?? selected.previous_record)?.drug_code ?? '미매칭'}</dd>
     <dt>원본 제품명</dt><dd>{(selected.current_record ?? selected.previous_record)?.product_name_raw}</dd>
     <dt>정규화 제품명</dt><dd>{(selected.current_record ?? selected.previous_record)?.product_name_normalized ?? '미정규화'}</dd>
     <dt>1회 투약량</dt><dd>{(selected.current_record ?? selected.previous_record)?.dose_per_administration ?? '미확인'} {(selected.current_record ?? selected.previous_record)?.unit}</dd>
    </dl>}
    {tab === '성분·함량' && <>
     <p>{ingredientText(selected.current_record ?? selected.previous_record)}</p>
     <p>제품 성분 함량: {strengthText(selected.current_record ?? selected.previous_record)}</p>
    </>}
    {tab === '공식 근거' && <>
     <p>{localMockNotice} 실제 식약처 API 검증 완료를 의미하지 않습니다.</p>
     <a href="https://nedrug.mfds.go.kr/" target="_blank" rel="noreferrer">식약처 의약품안전나라 포털 열기 ↗</a>
     <small className="block">포털 링크는 이 제품에 대한 매칭 근거가 아닙니다.</small>
    </>}
    {tab === '변경 이력' && selectedTimeline && <>
     <div className="timeline-comparison">
      {[
       { title: '이전 기록', snapshot: selectedTimeline.previous },
       { title: '현재 기록', snapshot: selectedTimeline.current },
      ].map(({ title, snapshot }) => <article key={title} className="timeline-snapshot">
       <h3>{title}</h3>
       <dl>
        <dt>기록일</dt><dd>{snapshot.recordDate}</dd>
        <dt>제품명</dt><dd>{snapshot.productName}</dd>
        <dt>성분</dt><dd>{snapshot.ingredient}</dd>
        <dt>제품 함량</dt><dd>{snapshot.productStrength}</dd>
        <dt>1회 투약량</dt><dd>{snapshot.dosePerAdministration}</dd>
        <dt>하루 투여횟수</dt><dd>{snapshot.administrationsPerDay}</dd>
       </dl>
      </article>)}
     </div>
     <div className="timeline-status">
      <strong>변경 상태: {labels[selectedTimeline.status]}</strong>
      <p>{reconciliationDescriptions[selectedTimeline.status]}</p>
      <small>엔진 사유 코드: {selected.reason_code}</small>
     </div>
    </>}
   </section>
  </div>}
 </div>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
