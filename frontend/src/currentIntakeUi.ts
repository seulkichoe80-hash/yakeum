import type { CurrentIntakeState, Item } from './types';

export type IntakeChoice = 'TAKING' | 'NOT_TAKING' | 'UNKNOWN';
export type CurrentIntakeStore = Record<string, Record<string, CurrentIntakeState>>;

export const intakeChoiceLabels: Record<IntakeChoice, string> = {
 TAKING: '먹고 있음',
 NOT_TAKING: '먹지 않음',
 UNKNOWN: '잘 모르겠음',
};

export const verificationLabels: Record<CurrentIntakeState['verification_status'], string> = {
 PENDING: '확인 전',
 USER_VERIFIED: '사용자 확인 완료',
};

function itemRecordId(item: Item): string | null {
 return item.current_record?.record_id ?? item.previous_record?.record_id ?? null;
}

export function initialCurrentIntakeState(
 familyMemberId: string,
 medicationRecordId: string,
): CurrentIntakeState {
 return {
  family_member_id: familyMemberId,
  medication_record_id: medicationRecordId,
  intake_status: 'UNKNOWN',
  verification_status: 'PENDING',
  verified_by: null,
  last_verified_at: null,
 };
}

export function buildInitialFamilyIntakeStates(
 familyMemberId: string,
 items: Item[],
 serverStates: CurrentIntakeState[] = [],
): Record<string, CurrentIntakeState> {
 const serverRecordIds = new Set(
  serverStates
   .filter(state => state.family_member_id === familyMemberId)
   .map(state => state.medication_record_id),
 );
 const recordIds = new Set(items.map(itemRecordId).filter((value): value is string => value !== null));
 serverRecordIds.forEach(recordId => recordIds.add(recordId));
 return Object.fromEntries(
  [...recordIds].map(recordId => [recordId, initialCurrentIntakeState(familyMemberId, recordId)]),
 );
}

export function replaceFamilyIntakeStates(
 store: CurrentIntakeStore,
 familyMemberId: string,
 items: Item[],
 serverStates: CurrentIntakeState[] = [],
): CurrentIntakeStore {
 return {
  ...store,
  [familyMemberId]: buildInitialFamilyIntakeStates(familyMemberId, items, serverStates),
 };
}

export function verifyCurrentIntake(
 store: CurrentIntakeStore,
 familyMemberId: string,
 medicationRecordId: string,
 choice: IntakeChoice,
 verifiedAt = new Date().toISOString(),
): CurrentIntakeStore {
 const current = store[familyMemberId]?.[medicationRecordId];
 if (!current) throw new Error('확인할 Current Intake State를 찾을 수 없습니다.');
 return {
  ...store,
  [familyMemberId]: {
   ...store[familyMemberId],
   [medicationRecordId]: {
    ...current,
    intake_status: choice,
    verification_status: 'USER_VERIFIED',
    verified_by: 'LOCAL_BROWSER_DEMO',
    last_verified_at: verifiedAt,
   },
  },
 };
}

export function getCurrentIntakeState(
 store: CurrentIntakeStore,
 familyMemberId: string,
 medicationRecordId: string | null,
): CurrentIntakeState | undefined {
 return medicationRecordId ? store[familyMemberId]?.[medicationRecordId] : undefined;
}
