import type { ResultBatches } from './types';
import { extractionSourceLabel, officialModeLabel } from './display';
// Hidden tab panels remain mounted. Never steal focus from another task.
export function focusVisible(element:HTMLElement|null){if(element&&element.getClientRects().length&&!element.closest('[hidden]')){element.focus();element.scrollIntoView({block:'nearest',behavior:'smooth'});}}
export function ProcessingSource({mode,sources,saved,batches,kind='photo'}:{mode?:string;sources?:{previous?:string;current?:string};saved:boolean;batches?:ResultBatches;kind?:'photo'|'hira'}){
 const rows=batches?[...batches.previous,...batches.current]:[];
 const official=rows.filter(r=>r.status==='MATCHED'&&r.match.source==='MFDS_DRUG'&&r.match.official_id).length;
 return <div className="processing-source" aria-label="처리 출처와 저장 상태">
  <p>사진 읽기: {sources?`이전 ${extractionSourceLabel(sources.previous??'UNKNOWN')} / 현재 ${extractionSourceLabel(sources.current??'UNKNOWN')}`:kind==='hira'?'사진 추출 없음 · HIRA 파일 처리':'사진 추출 출처 확인 필요'}</p>
  <p>의약품 확인: {officialModeLabel(mode??'UNKNOWN')}{mode==='MFDS_LIVE'&&` · 실제 매칭 확정 ${official}건 (응답 근거)`}</p>
  <strong>{saved?'✓ 저장 완료':'○ 저장 전'}</strong>
 </div>;
}
export function MedicineReview({batches}:{batches:ResultBatches}){
 const names={MATCHED:'대응 정보 확인',PARTIAL:'일부 정보만 확인',UNMATCHED:'대응 제품 확인 필요',FAILED:'의약품 정보 처리 실패'};
 return <section aria-label="비교 전 의약품 정보 검토"><h4>비교 전에 확인할 의약품 정보</h4><p>사진 내용 확인과 다른 단계입니다. 보완된 성분·함량과 경고를 확인하세요.</p><div className="record-pair">{(['previous','current'] as const).map(side=><section key={side}><h5>{side==='previous'?'이전':'현재'} 자료</h5>{batches[side].map((r,i)=><article className="card" key={i}><strong>{r.record?.product_name_normalized??r.record?.product_name_raw??'제품 확인 필요'} · {names[r.status]}</strong><dl>{r.record?<><dt>성분·함량</dt><dd>{r.record.ingredients.map(g=>`${g.ingredient_name_normalized??g.ingredient_name_raw??'미확인'} / ${g.product_strength??'미확인'} ${g.product_strength_unit??'(단위 미확인)'}`).join(', ')||'미확인'}</dd><dt>1회 투약량 / 하루 횟수</dt><dd>{r.record.dose_per_administration??'미확인'} {r.record.unit??'(단위 미확인)'} / {r.record.administrations_per_day??'미확인'}회</dd></>:<><dt>후보 정보</dt><dd>의약품 정보를 확인하지 못했습니다. 기록이 없다는 뜻이 아닙니다.</dd></>}</dl>{[...r.warnings,...r.errors].length>0&&<ul role="status">{[...r.warnings,...r.errors].map((w,n)=><li key={n}>{w.message}</li>)}</ul>}</article>)}</section>)}</div></section>;
}
