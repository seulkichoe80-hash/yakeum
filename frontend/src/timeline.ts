import type { Item, MedicationRecord, Status } from './types';

export type MedicationSnapshot = {
 presence: 'present' | 'absent' | 'unknown';
 recordDate: string;
 productName: string;
 ingredient: string;
 productStrength: string;
 dosePerAdministration: string;
 administrationsPerDay: string;
};

export type MedicationTimeline = {
 previous: MedicationSnapshot;
 current: MedicationSnapshot;
 status: Status;
};

export function safeValue(value: string | null | undefined): string {
 return value === null || value === undefined || value === '' ? '미확인' : value;
}

function ingredientNames(record: MedicationRecord | null): string {
 if (!record || record.ingredients.length === 0) return '미확인';
 const names = record.ingredients
  .map(ingredient => ingredient.ingredient_name_normalized ?? ingredient.ingredient_name_raw)
  .filter((value): value is string => Boolean(value));
 return names.length > 0 ? names.join(', ') : '미확인';
}

function productStrength(record: MedicationRecord | null): string {
 if (!record || record.ingredients.length === 0) return '미확인';
 const values = record.ingredients.map(ingredient => {
  if (ingredient.product_strength == null || ingredient.product_strength === '') return '미확인';
  return `${ingredient.product_strength}${ingredient.product_strength_unit ? ` ${ingredient.product_strength_unit}` : ''}`;
 });
 return values.length > 0 ? values.join(' / ') : '미확인';
}

function dosePerAdministration(record: MedicationRecord | null): string {
 if (!record || record.dose_per_administration == null || record.dose_per_administration === '') return '미확인';
 return `${record.dose_per_administration}${record.unit ? ` ${record.unit}` : ''}`;
}

function administrationsPerDay(record: MedicationRecord | null): string {
 if (!record || record.administrations_per_day == null || record.administrations_per_day === '') return '미확인';
 return `${record.administrations_per_day}회`;
}

export function medicationSnapshot(record: MedicationRecord | null | undefined): MedicationSnapshot {
 return {
  presence: record===null?'absent':record===undefined?'unknown':'present',
  recordDate: safeValue(record?.record_date),
  productName: safeValue(record?.product_name_normalized ?? record?.product_name_raw),
  ingredient: ingredientNames(record??null),
  productStrength: productStrength(record??null),
  dosePerAdministration: dosePerAdministration(record??null),
  administrationsPerDay: administrationsPerDay(record??null),
 };
}

export function medicationTimeline(item: Item): MedicationTimeline {
 return {
  previous: medicationSnapshot(item.previous_record),
  current: medicationSnapshot(item.current_record),
  status: item.status,
 };
}

// Only an explicit null on an executed comparison item establishes absence.
export function recordSummary(record:MedicationRecord|null|undefined,side:'이전'|'현재'):string {
 const snapshot=medicationSnapshot(record);
 if(snapshot.presence==='absent')return `${side}: 기록 없음`;
 if(snapshot.presence==='unknown')return `${side}: 기록 확인 필요`;
 return `${side}: ${snapshot.recordDate} · ${snapshot.productStrength} · ${snapshot.dosePerAdministration}`;
}
