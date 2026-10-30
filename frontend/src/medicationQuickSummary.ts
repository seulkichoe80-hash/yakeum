import type {MedicationRecord,ReconciliationItem} from './types';
const value=(v:string|null|undefined)=>v==null||v===''?'미확인':v;
export function medicationQuickSummary(record:MedicationRecord|null|undefined):string{
 if(record===null)return '기록 없음';if(record===undefined)return '기록 확인 필요';
 const compound=record.ingredients.length>1;
 const strengths=record.ingredients.map(i=>{
  const amount=i.product_strength==null||i.product_strength===''?'함량 미확인':`${i.product_strength}${i.product_strength_unit||' (단위 미확인)'}`;
  return compound?`${value(i.ingredient_name_normalized??i.ingredient_name_raw)} ${amount}`:amount;
 }).join(' / ')||'함량 미확인';
 const dose=record.dose_per_administration==null||record.dose_per_administration===''?'한 번 투약량 미확인':`한 번에 ${record.dose_per_administration}${record.unit||' (단위 미확인)'}`;
 const perDay=record.administrations_per_day==null||record.administrations_per_day===''?'하루 횟수 미확인':`하루 ${record.administrations_per_day}회`;
 return `${strengths} · ${dose} · ${perDay}`;
}
export function comparisonQuickSummary(item:ReconciliationItem):{label:string;text:string}[]{
 // Explicit absence is shown even while the other side contains known medication values.
 if(item.previous_record===null||item.current_record===null||item.previous_record===undefined||item.current_record===undefined)
  return [{label:'이전',text:medicationQuickSummary(item.previous_record)},{label:'현재',text:medicationQuickSummary(item.current_record)}];
 return [{label:'',text:medicationQuickSummary(item.current_record)}];
}
