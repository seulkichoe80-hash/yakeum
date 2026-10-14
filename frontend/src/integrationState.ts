import type { VerticalSliceResponse } from './types';

export type IntegrationState = {
 memberId: string;
 phase: 'idle' | 'loading' | 'success' | 'error';
 response: VerticalSliceResponse | null;
 error: string | null;
};

export type IntegrationAction =
 | { type: 'memberChanged'; memberId: string }
 | { type: 'started'; memberId: string }
 | { type: 'succeeded'; memberId: string; response: VerticalSliceResponse }
 | { type: 'failed'; memberId: string; error: string };

export function initialIntegrationState(memberId: string): IntegrationState {
 return { memberId, phase: 'idle', response: null, error: null };
}

export function integrationReducer(state: IntegrationState, action: IntegrationAction): IntegrationState {
 if (action.type === 'memberChanged') return initialIntegrationState(action.memberId);
 if (action.memberId !== state.memberId) return state;
 if (action.type === 'started') return { ...state, phase: 'loading', response: null, error: null };
 if (action.type === 'failed') return { ...state, phase: 'error', response: null, error: action.error };
 return { ...state, phase: 'success', response: action.response, error: null };
}
