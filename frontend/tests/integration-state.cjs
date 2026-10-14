const assert = require('node:assert/strict');
const { initialIntegrationState, integrationReducer } = require('../src/integrationState.ts');

const familyA = '00000000-0000-4000-8000-000000000001';
const familyB = '00000000-0000-4000-8000-000000000002';
let state = initialIntegrationState(familyA);
state = integrationReducer(state, { type: 'started', memberId: familyA });
assert.equal(state.phase, 'loading');
state = integrationReducer(state, { type: 'failed', memberId: familyA, error: '가상 오류' });
assert.equal(state.phase, 'error');
assert.equal(state.error, '가상 오류');
state = integrationReducer(state, { type: 'started', memberId: familyA });
assert.equal(state.phase, 'loading', 'retry returns to loading');
state = integrationReducer(state, { type: 'memberChanged', memberId: familyB });
assert.deepEqual(state, { memberId: familyB, phase: 'idle', response: null, error: null });
const stale = integrationReducer(state, { type: 'failed', memberId: familyA, error: 'stale' });
assert.equal(stale, state, 'a response for the previous family must be ignored');
console.log('Integration UI state checks passed: loading, error, retry, and family reset.');
