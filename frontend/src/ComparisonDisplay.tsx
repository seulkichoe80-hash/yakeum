import { medicationSnapshot, recordSummary } from './timeline';
import type { MedicationRecord, ReconciliationItem } from './types';
import { comparisonBadge,comparisonChanges,comparisonColorNotice,comparisonScopeNotice } from './comparisonDisplay';
export function ComparisonBadge({status}:{status:string}){const badge=comparisonBadge(status);return <span className={`comparison-badge comparison-${badge.tone}`}>{badge.text}</span>;}
export function ComparisonNotice(){return <div className="comparison-notice"><p>{comparisonColorNotice}</p><p>{comparisonScopeNotice}</p></div>;}
export function ComparisonChanges({item}:{item:ReconciliationItem}){const rows=comparisonChanges(item);return rows.length?<ul className="comparison-changes" aria-label="이전과 현재 값의 차이">{rows.map(row=><li key={row.label}>{row.label}: <strong>{row.before} → {row.after}</strong></li>)}</ul>:null;}

export function RecordSummary({record,side}:{record:MedicationRecord|null|undefined;side:'이전'|'현재'}){
 const v=medicationSnapshot(record);
 return <section className="record-summary" aria-label={`${side} 복용정보`}><h5>{side}</h5><p>{recordSummary(record,side)}</p>{v.presence==='present'&&<><dl>{[['성분',record?.ingredients.map(i=>i.ingredient_name_normalized??i.ingredient_name_raw??'미확인').join(' / ')||'미확인'],['성분 함량',v.productStrength],['1회 투약량',v.dosePerAdministration],['투약 단위',record?.unit??'미확인'],['하루 횟수',v.administrationsPerDay]].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl><small>자료 기준일 {v.recordDate} · 투약 기간 {record?.duration_days==null?'미확인':`${record.duration_days}일`}<br/>날짜·기간은 비교 판정 기준과 별도입니다.</small></>}</section>;
}
