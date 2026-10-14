import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { initialMembers, mockResult, labels, statuses, primaryMemberId, productName, ingredientText, strengthText, type Status, type Item, type Member } from './domain';
import './style.css';
import { fileError, reviewError } from './validation';

function App() {
 const [members, setMembers] = useState(initialMembers);
 const [memberId, setMemberId] = useState(primaryMemberId);
 const member = members.find(m => m.id === memberId)!;
 const [page, setPage] = useState('overview');
 const [filter, setFilter] = useState<Status | 'ALL'>('ALL');
 const [query, setQuery] = useState('');
 const [selected, setSelected] = useState<Item | null>(null);
 const [notice, setNotice] = useState('');
 const [source, setSource] = useState('약봉투 사진');
 const [file, setFile] = useState<File | null>(null);
 const [date, setDate] = useState('2026-10-08');
 const [uploadState, setUploadState] = useState<'idle' | 'review' | 'done'>('idle');
 const [product, setProduct] = useState('');
 const [strength, setStrength] = useState('');
 const [unit, setUnit] = useState('');
 const [confirmed, setConfirmed] = useState(false);
 const [name, setName] = useState('');
 const [relation, setRelation] = useState('');
 const [resolved, setResolved] = useState<string[]>([]);
 const [tab, setTab] = useState('기본정보');
 const dialogRef = useRef<HTMLElement>(null);
 const openerRef = useRef<HTMLElement | null>(null);
 const [month, setMonth] = useState('2026-09');
 const allowed = member.consent && member.approved;
 const items = memberId === primaryMemberId ? mockResult.items : [];
 const pending = items.filter(i => i.status === 'NEEDS_CONFIRMATION' && !resolved.includes(i.id));
 const visible = items.filter(i => (filter === 'ALL' || i.status === filter) && productName((i.current_record ?? i.previous_record)).includes(query));
 function resetUpload() { setUploadState('idle'); setConfirmed(false); setProduct(''); setStrength(''); setUnit(''); setNotice(''); }
 function switchMember(id: string) { setMemberId(id); setSelected(null); setFile(null); resetUpload(); setQuery(''); setFilter('ALL'); setMonth('2026-09'); }
 function openDetails(item: Item, detailTab: string) { openerRef.current = document.activeElement as HTMLElement; setSelected(item); setTab(detailTab); }
 const inputError = reviewError(product, strength, unit);
 useEffect(() => {
  if (!selected || !allowed) return;
  const oldOverflow = document.body.style.overflow;
  const background = Array.from(document.querySelectorAll<HTMLElement>('aside, main')).map(element => ({ element, wasInert: element.inert }));
  background.forEach(({element}) => { element.inert = true; });
  document.body.style.overflow = 'hidden';
  dialogRef.current?.querySelector<HTMLButtonElement>('button')?.focus();
  const onKey = (event: KeyboardEvent) => {
   if (event.key === 'Escape') { event.preventDefault(); setSelected(null); return; }
   if (event.key !== 'Tab') return;
   const controls = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>('button, a[href], input, select, textarea, [tabindex="0"]') ?? []).filter(element => !element.hasAttribute('disabled') && element.getClientRects().length > 0);
   const first = controls[0], last = controls[controls.length - 1];
   if (!first) { event.preventDefault(); return; }
   if (event.shiftKey && (document.activeElement === first || !dialogRef.current?.contains(document.activeElement))) { event.preventDefault(); last.focus(); }
   else if (!event.shiftKey && (document.activeElement === last || !dialogRef.current?.contains(document.activeElement))) { event.preventDefault(); first.focus(); }
  };
  document.addEventListener('keydown', onKey);
  return () => {
   document.removeEventListener('keydown', onKey);
   document.body.style.overflow = oldOverflow;
   background.forEach(({element,wasInert}) => { element.inert = wasInert; });
   if (openerRef.current?.isConnected) openerRef.current.focus({preventScroll:true});
  };
 }, [selected, allowed]);
 function patchMember(patch: Partial<Member>) { setMembers(ms => ms.map(m => m.id === memberId ? { ...m, ...patch } : m)); }
 function register() {
  if (!allowed) return setNotice('먼저 정보 처리 동의와 가족 열람 승인을 완료해 주세요.');
  if (!file || !date) return setNotice('파일과 자료 기준일을 선택해 주세요.');
  const error = fileError(file.name, file.size, source === '심평원 Excel');
  if (error) { setUploadState('idle'); setConfirmed(false); return setNotice(error); }
  setProduct(''); setStrength(''); setUnit(''); setConfirmed(false); setUploadState('review'); setNotice('데모 확인 화면입니다. 파일은 서버로 전송되지 않으며 실제 AI 인식은 실행하지 않습니다.');
 }
 return <div className="shell">
  <aside><a className="logo" href="#" onClick={() => setPage('overview')}><span>＋</span> 약이음</a><p className="subtitle">가족을 잇는 복용정보</p><nav>{[['overview','◫','가족 대시보드'],['upload','↥','자료 등록'],['inbox','✓','확인함'],['family','♧','가족 · 동의 관리']].map(([key, icon, text]) => <button key={key} className={page === key ? 'active' : ''} onClick={() => {setPage(key);setNotice('');}}>{icon}　{text}{key === 'inbox' && allowed && pending.length > 0 && <b>{pending.length}</b>}</button>)}</nav><div className="aside-bottom">함께 확인하고,<br/>더 정확하게 기록해요.<small>복용정보 정리 및 상담 보조 서비스</small></div></aside>
  <main><header><div className="breadcrumb">우리 가족 / {page === 'overview' ? '대시보드' : page === 'upload' ? '자료 등록' : page === 'inbox' ? '확인함' : '가족 관리'}</div><span className="demo">MOCK · 가상 데이터</span></header>
   <div className="heading"><div><p className="eyebrow">FAMILY MEDICATION RECORD</p><h1>{page === 'overview' ? '우리 가족 복용정보' : page === 'upload' ? '새 자료 등록' : page === 'inbox' ? '함께 확인할 정보' : '가족과 동의 관리'}</h1><p>흩어진 기록을 모아, 지난 기록과의 변화를 확인하세요.</p></div><label className="member-select">가족 구성원<select value={memberId} onChange={e => switchMember(e.target.value)}>{members.map(m => <option key={m.id} value={m.id}>{m.relationship} · {m.name}</option>)}</select></label></div>
   <div className="info">이 화면은 가상 데이터 데모입니다. 표시된 변화는 복용 변경 지시가 아니며, 불확실한 정보는 가족·전문가와 확인해 주세요.</div>
   {notice && <div className="notice" role="status">{notice}</div>}
   {!allowed && page !== 'family' ? <section className="card empty"><h2>동의와 승인이 필요해요</h2><p>선택한 가족의 정보 처리 동의와 가족 열람 승인을 확인해 주세요.</p><button className="primary" onClick={() => setPage('family')}>동의 관리 열기</button></section> : <>
   {page === 'overview' && <>
    <div className="stats">{statuses.map(status => <button key={status} className={'stat ' + status + (filter === status ? ' chosen' : '')} onClick={() => setFilter(filter === status ? 'ALL' : status)}><span>{labels[status]}</span><strong>{items.filter(i => i.status === status).length}<small>건</small></strong><p>{status === 'MAINTAINED' ? '이전 기록과 동일' : status === 'NEW' ? '새로 확인된 기록' : status === 'DOSE_CHANGED' ? '기록된 함량 변화' : '최신 자료에서 미확인'}</p></button>)}</div>
    <section className="card timeline"><div><h2>복용정보 타임라인</h2><p>기준 자료: 2026년 8월 → 9월 · D 엔진 결과 예시</p></div><div className="months">{['2026-03','2026-08','2026-09'].map(m => <button className={month === m ? 'current' : ''} key={m} onClick={() => setMonth(m)}>{m.slice(5)}월<span>●</span></button>)}</div></section>
    {month !== '2026-09' ? <section className="card empty"><h2>{month} 기록 미제공</h2><p>이번 데모에는 9월 비교 결과와 개별 항목의 8월 이전 기록이 포함되어 있습니다.</p><button onClick={() => setMonth('2026-09')}>9월 보기</button></section> : <section className="card"><div className="section-heading"><div><h2>{member.relationship}의 기록 비교</h2><p>현재 자료 {items.filter(i => i.current_record).length}건 · 확인 필요 {pending.length}건</p></div><button className="primary" onClick={() => setPage('upload')}>＋ 자료 등록</button></div><div className="toolbar"><label>제품 검색 <input value={query} onChange={e => setQuery(e.target.value)} placeholder="제품명으로 검색"/></label><select aria-label="변경 상태 필터" value={filter} onChange={e => setFilter(e.target.value as Status | 'ALL')}><option value="ALL">전체 상태</option>{statuses.map(s => <option key={s} value={s}>{labels[s]}</option>)}</select></div><div className="records">{visible.map(i => <button key={i.id} className="record" onClick={() => openDetails(i, '기본정보')}><span className="pill-icon">◇</span><span className="record-name"><strong>{productName((i.current_record ?? i.previous_record))}</strong><small>{ingredientText((i.current_record ?? i.previous_record))} · {strengthText((i.current_record ?? i.previous_record))} </small><small>{(i.current_record ?? i.previous_record)?.user_confirmed ? '사용자 확인됨' : '사용자 미확정 후보'}</small></span><span className={'badge ' + i.status}>{labels[i.status]}</span><span className="record-date">{i.current_record ? i.current_record.record_date : '현재 자료 없음'}</span><span>›</span></button>)}{visible.length === 0 && <p className="empty">조건에 맞는 기록이 없습니다.</p>}</div></section>}
   </>}
   {page === 'upload' && <section className="card form"><h2>자료를 등록할 가족과 기준일을 확인해 주세요</h2><p>파일 선택 → 추출 결과 확인 → 사용자 확정 → 정규화 · 비교 결과 확인</p><label>자료 유형<select value={source} onChange={e => {setSource(e.target.value);setFile(null);resetUpload();}}>{['심평원 Excel','약봉투 사진','처방전 사진','건강기능식품 사진'].map(s => <option key={s}>{s}</option>)}</select></label><label>자료 기준일<input type="date" value={date} onChange={e => {setDate(e.target.value);resetUpload();}}/></label><label className="dropzone">↥<strong>{file?.name ?? '파일을 선택해 주세요'}</strong><span>{source === '심평원 Excel' ? 'XLSX, XLS' : 'JPG, PNG, WEBP'} · 최대 10MB</span><input key={`${memberId}:${source}`} type="file" accept={source === '심평원 Excel' ? '.xlsx,.xls' : '.jpg,.jpeg,.png,.webp'} onChange={e => {setFile(e.target.files?.[0] ?? null);resetUpload();}}/></label><button className="primary" onClick={register}>확인 화면으로 이동 (데모)</button>
    {uploadState === 'review' && <div className="review"><h2>추출 결과 수정·확정</h2><p>실제 인식 결과가 없으므로 확인할 값을 직접 입력하세요. 저장은 현재 화면의 데모 상태에만 반영됩니다.</p><label>제품명<input value={product} onChange={e => setProduct(e.target.value)}/></label><div className="row"><label>함량 (선택)<input type="text" inputMode="decimal" value={strength} aria-describedby="review-error" onChange={e => setStrength(e.target.value)}/></label><label>단위 (선택)<input aria-describedby="review-error" value={unit} onChange={e => setUnit(e.target.value)} placeholder="예: mg"/></label></div><p id="review-error" className="field-error" role="status">{(product || strength || unit) && inputError}</p><label className="check"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/>원본 자료와 입력 내용을 대조했습니다.</label><button className="primary" disabled={!confirmed || inputError !== null} onClick={() => {setUploadState('done');setNotice('사용자 확정 데모 완료. 실제 저장·정규화·비교는 API 연동 후 실행됩니다.');}}>입력 내용 확정 (데모)</button></div>}
    {uploadState === 'done' && <div className="info">{member.name} · {product} · {date} 입력을 확인했습니다. 대시보드의 가상 비교 결과는 그대로 유지됩니다.</div>}
   </section>}
   {page === 'inbox' && <section className="card"><h2>최신 자료에서 확인되지 않은 항목</h2><p>자료에서 보이지 않는다는 이유만으로 복용 중단으로 처리하지 않습니다.</p>{pending.map(i => <div className="pending" key={i.id}><div><strong>{productName(i.previous_record)}</strong><p>이전 기록 {i.previous_record?.record_date} · 현재 기록 없음</p></div><button onClick={() => openDetails(i, '변경 이력')}>기록 살펴보기</button><button className="primary" onClick={() => {setResolved([...resolved,i.id]);setNotice('확인 표시를 남겼습니다(데모). 복용상태와 엔진 판정은 변경되지 않습니다.');}}>검토 완료 표시</button></div>)}{pending.length === 0 && <div className="empty">지금 확인할 항목이 없습니다.</div>}</section>}
   {page === 'family' && <section className="card form"><h2>{member.name}님의 정보 접근</h2><p>아래 체크는 UI 시연용입니다. 실제 동의·승인 및 접근권한은 서버에서 검증해야 합니다.</p><label className="check"><input type="checkbox" checked={member.consent} onChange={e => patchMember({consent:e.target.checked})}/>건강정보 수집·처리 동의 (데모)</label><label className="check"><input type="checkbox" checked={member.approved} onChange={e => patchMember({approved:e.target.checked})}/>가족 열람 승인 (데모)</label><hr/><h2>가족 구성원 추가</h2><label>이름<input value={name} onChange={e => setName(e.target.value)}/></label><label>관계<input value={relation} onChange={e => setRelation(e.target.value)} placeholder="예: 본인, 아버지"/></label><button className="primary" disabled={!name.trim() || !relation.trim()} onClick={() => {const id = crypto.randomUUID();setMembers([...members,{id,name:name.trim(),relationship:relation.trim(),consent:false,approved:false}]);switchMember(id);setName('');setRelation('');}}>가족 추가 (데모)</button></section>}
   </>}
   <footer>약이음은 복용정보를 정리합니다. 진단·처방·복용량 변경·복용 중단을 안내하지 않습니다.<br/>데모 입력은 메모리에만 유지되며 새로고침하면 초기화됩니다.</footer>
  </main>
  {selected && allowed && <div className="overlay" onClick={() => setSelected(null)}><section ref={dialogRef} className="detail" role="dialog" aria-modal="true" aria-label="복용정보 상세" onClick={e => e.stopPropagation()}><div className="section-heading"><h2>{productName((selected.current_record ?? selected.previous_record))}</h2><button autoFocus onClick={() => setSelected(null)} aria-label="상세 닫기">닫기 ×</button></div><span className={'badge ' + selected.status}>{labels[selected.status]}</span><div className="tabs">{['기본정보','성분·함량','공식 근거','변경 이력'].map(t => <button className={tab === t ? 'active' : ''} key={t} onClick={() => setTab(t)}>{t}</button>)}</div>{tab === '기본정보' && <dl><dt>자료 기준일</dt><dd>{(selected.current_record ?? selected.previous_record)?.record_date}</dd><dt>복용법</dt><dd>{(selected.current_record ?? selected.previous_record)?.dosage_text_raw ?? '미확인'}</dd><dt>공식 제품 코드</dt><dd>{(selected.current_record ?? selected.previous_record)?.drug_code ?? '미매칭 (데모)'}</dd><dt>원본 제품명</dt><dd>{(selected.current_record ?? selected.previous_record)?.product_name_raw}</dd><dt>정규화 제품명</dt><dd>{(selected.current_record ?? selected.previous_record)?.product_name_normalized ?? '미정규화'}</dd><dt>1회 투약량</dt><dd>{(selected.current_record ?? selected.previous_record)?.dose_per_administration ?? '미확인'} {(selected.current_record ?? selected.previous_record)?.unit}</dd></dl>}{tab === '성분·함량' && <><p>{ingredientText((selected.current_record ?? selected.previous_record))}</p><p>기록 함량: {strengthText((selected.current_record ?? selected.previous_record))} </p></>}{tab === '공식 근거' && <><p>이 가상 제품에는 공식 근거가 연결되어 있지 않습니다. 제품별 근거는 B·D API가 반환한 검증된 출처만 표시합니다.</p><a href="https://nedrug.mfds.go.kr/" target="_blank" rel="noreferrer">식약처 의약품안전나라 포털 열기 ↗</a><small className="block">포털 링크는 이 제품에 대한 매칭 근거가 아닙니다.</small></>}{tab === '변경 이력' && <><p>이전: {selected.previous_record ? `${selected.previous_record.record_date} · ${strengthText(selected.previous_record)}` : '이전 기록 없음'}</p><p>현재: {selected.current_record ? `${selected.current_record.record_date} · ${strengthText(selected.current_record)}` : '최신 자료에서 미확인'}</p><p>엔진 사유 코드: {selected.reason_code}</p></>}</section></div>}
 </div>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
