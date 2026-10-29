import type { MedicationRecord, ReconciliationItem } from './types';
export const comparisonBadges={
 MAINTAINED:{tone:'same',text:'＝ 기록 동일'},
 DOSE_CHANGED:{tone:'changed',text:'↔ 복용정보 변경'},
 NEW:{tone:'new',text:'＋ 새로 확인'},
 NEEDS_CONFIRMATION:{tone:'previous',text:'－ 이전에만 있음'},
 HELD:{tone:'held',text:'! 추가 확인 필요'},
} as const;
export function comparisonBadge(status:string){return Object.hasOwn(comparisonBadges,status)?comparisonBadges[status as keyof typeof comparisonBadges]:{tone:'unknown',text:'? 비교 상태 확인 필요'};}
export const comparisonColorNotice='색상과 기호는 기록의 차이이며 의학적 안전·위험 판정이 아닙니다. 실제 복용 상태는 별도로 확인합니다. 이전에만 있다는 이유로 복용 중단을 뜻하지 않습니다.';
export const comparisonScopeNotice='기록 동일은 비교 가능한 성분·함량·1회 투약량·단위·하루 횟수 기준입니다. 날짜·기간·메모까지 모두 같다는 뜻은 아닙니다.';
function decimal(value:string|null){if(value===null)return null;const m=/^([+-]?)(\d+)(?:\.(\d*))?$/.exec(value);if(!m)return value;const whole=m[2].replace(/^0+(?=\d)/,'');const fraction=(m[3]??'').replace(/0+$/,'');return `${m[1]==='-'&&(whole!=='0'||fraction)?'-':''}${whole}${fraction?'.'+fraction:''}`;}
const known=(v:string|null)=>v===null||v===''?'미확인':v;
const quantity=(v:string|null,suffix:string)=>v===null||v===''?'미확인':v+suffix;
function strength(record:MedicationRecord){return record.ingredients.map(i=>`${known(i.ingredient_name_normalized??i.ingredient_name_raw)} ${known(i.product_strength)} ${i.product_strength_unit??''}`.trim()).join(' / ')||'미확인';}
function strengthKey(record:MedicationRecord){return JSON.stringify(record.ingredients.map(i=>[i.official_ingredient_id??i.ingredient_name_normalized??i.ingredient_name_raw,decimal(i.product_strength),i.product_strength_unit]).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b))));}
export function comparisonChanges(item:ReconciliationItem){
 const p=item.previous_record,c=item.current_record;if(!p||!c)return [];
 const rows=[
  {label:'제품 함량',before:strength(p),after:strength(c),changed:strengthKey(p)!==strengthKey(c)},
  {label:'1회 투약량',before:`${known(p.dose_per_administration)} ${p.unit??''}`.trim(),after:`${known(c.dose_per_administration)} ${c.unit??''}`.trim(),changed:decimal(p.dose_per_administration)!==decimal(c.dose_per_administration)||p.unit!==c.unit},
  {label:'하루 횟수',before:quantity(p.administrations_per_day,'회'),after:quantity(c.administrations_per_day,'회'),changed:decimal(p.administrations_per_day)!==decimal(c.administrations_per_day)},
  {label:'투약 기간',before:quantity(p.duration_days,'일'),after:quantity(c.duration_days,'일'),changed:decimal(p.duration_days)!==decimal(c.duration_days)},
 ];return rows.filter(r=>r.changed);
}
