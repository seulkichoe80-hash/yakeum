import {comparisonQuickSummary} from './medicationQuickSummary';
import {useId} from 'react';
import {ComparisonBadge,ComparisonChanges,RecordSummary} from './ComparisonDisplay';
import type {ReconciliationItem,ResultBatches} from './types';
import {productName} from './types';
import {intakeChoiceLabels,type IntakeChoice} from './currentIntakeUi';
export function ResultSummary({family,items,held,dates,holdCount,headingRef}:{family:string;items:ReconciliationItem[]|null;held:boolean;dates?:string;holdCount?:number;headingRef?:React.Ref<HTMLHeadingElement>}){
 const states=['MAINTAINED','DOSE_CHANGED','NEW','NEEDS_CONFIRMATION'];
 return <header className="result-summary"><h2 ref={headingRef} tabIndex={-1}>{family} · {held?'추가 확인 필요':'비교 결과'}</h2>{dates&&<p>확인된 기록 기준일 {dates}</p>}{held?<div><p role="status">비교 보류 · 판정을 실행하지 않았습니다.</p>{holdCount!==undefined&&<strong>보류 사유 {holdCount}건</strong>}</div>:<ul>{['동일','변경','이번에만','이전에만'].map((label,i)=><li key={label}>{label} <strong>{items?.filter(x=>x.status===states[i]).length??0}</strong></li>)}</ul>}<p>기록의 차이이며 안전·위험 판정이나 복용 중단 지시가 아닙니다.</p></header>;
}
export function IntakeSelection({value,onChange,onClear,disabled=false}:{value?:IntakeChoice;onChange:(v:IntakeChoice)=>void;onClear?:()=>void;disabled?:boolean}){
 const id=useId();return <fieldset className="intake-options" disabled={disabled}><legend>실제 복용 상태</legend>{Object.entries(intakeChoiceLabels).map(([choice,label])=><label key={choice}><input type="radio" name={id} value={choice} checked={value===choice} onChange={()=>onChange(choice as IntakeChoice)}/>{label}</label>)}{!value&&<small>미선택 · 복용 확인 전</small>}{value&&onClear&&<button className="clear-intake" type="button" onClick={onClear}>선택 취소</button>}</fieldset>;
}
export function SimpleMedication({item,children}:{item:ReconciliationItem;children?:React.ReactNode}){
 const r=item.current_record??item.previous_record;
 return <article className="card simple-medication"><h3>{productName(r)}</h3><ComparisonBadge status={item.status}/><ComparisonChanges item={item}/><div className="medication-quick-summary" aria-label="주요 투약 정보">{comparisonQuickSummary(item).map(row=><p key={row.label}>{row.label&&`${row.label}: `}{row.text}</p>)}</div><details><summary>성분·이전/현재 상세 비교</summary><div className="record-pair"><RecordSummary side="이전" record={item.previous_record}/><RecordSummary side="현재" record={item.current_record}/></div><p>날짜·기간은 비교 판정 기준과 별도입니다.</p></details>{children}</article>;
}

export function batchDates(batches:ResultBatches){const dates=(side:'previous'|'current')=>[...new Set(batches[side].flatMap(r=>r.record?.record_date?[r.record.record_date]:[]))].sort().join(', ')||'미확인';return `이전 ${dates('previous')} → 현재 ${dates('current')}`;}
