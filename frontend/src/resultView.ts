import type { Item } from './types';

export type ResultViewMode = 'EMPTY' | 'MOCK' | 'BACKEND';

export type ResultViewState = {
 memberId: string;
 mode: ResultViewMode;
};

export type ResultViewAction =
 | { type: 'memberChanged'; memberId: string }
 | { type: 'backendStarted'; memberId: string }
 | { type: 'backendSucceeded'; memberId: string }
 | { type: 'mockSelected'; memberId: string };

export function initialResultViewState(memberId: string): ResultViewState {
 return { memberId, mode: 'EMPTY' };
}

export function resultViewReducer(state: ResultViewState, action: ResultViewAction): ResultViewState {
 if (action.type === 'memberChanged') return initialResultViewState(action.memberId);
 if (action.memberId !== state.memberId) return state;
 if (action.type === 'backendStarted') return { ...state, mode: 'EMPTY' };
 if (action.type === 'backendSucceeded') return { ...state, mode: 'BACKEND' };
 return { ...state, mode: 'MOCK' };
}

export function mockItemsForFamily(items: Item[], familyMemberId: string): Item[] {
 return items.map((item, index) => ({
  ...item,
  id: `mock-${familyMemberId}-${index}`,
  previous_record: item.previous_record
   ? { ...item.previous_record, family_member_id: familyMemberId }
   : null,
  current_record: item.current_record
   ? { ...item.current_record, family_member_id: familyMemberId }
   : null,
 }));
}
