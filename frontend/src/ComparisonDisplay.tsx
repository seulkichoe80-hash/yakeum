import { recordSummary } from './timeline';
import type { MedicationRecord, ReconciliationItem } from './types';
import { comparisonBadge,comparisonChanges,comparisonColorNotice,comparisonScopeNotice } from './comparisonDisplay';
export function ComparisonBadge({status}:{status:string}){const badge=comparisonBadge(status);return <span className={`comparison-badge comparison-${badge.tone}`}>{badge.text}</span>;}
export function ComparisonNotice(){return <div className="comparison-notice"><p>{comparisonColorNotice}</p><p>{comparisonScopeNotice}</p></div>;}
export function ComparisonChanges({item}:{item:ReconciliationItem}){const rows=comparisonChanges(item);return rows.length?<ul className="comparison-changes" aria-label="이전과 현재 값의 차이">{rows.map(row=><li key={row.label}>{row.label}: <strong>{row.before} → {row.after}</strong></li>)}</ul>:null;}

export function RecordSummary({record,side}:{record:MedicationRecord|null|undefined;side:'이전'|'현재'}){return <p>{recordSummary(record,side)}</p>;}
