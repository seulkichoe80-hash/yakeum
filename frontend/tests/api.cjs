const assert = require('node:assert/strict');
const { parseVerticalSliceResponse, ApiError } = require('../src/api.ts');
const { contractMock } = require('../src/mock.ts');

const familyId = contractMock.family_member_id;
const response = {
 processing: { parser: 'DETERMINISTIC', file_processing: 'EXECUTED', official_data_mode: 'LOCAL_MOCK', persisted: false },
 accepted_results: { previous: [], current: [] },
 review_results: { previous: [], current: [] },
 reconciliation_result: contractMock,
 current_intake_states: contractMock.items.map((item) => {
  const record = item.current_record ?? item.previous_record;
  return { family_member_id: familyId, medication_record_id: record.record_id, intake_status: 'UNKNOWN', verification_status: 'PENDING', verified_by: null, last_verified_at: null };
 }),
};

assert.equal(parseVerticalSliceResponse(response, familyId), response);
assert.throws(() => parseVerticalSliceResponse({ ...response, processing: { ...response.processing, official_data_mode: 'LIVE' } }, familyId), ApiError);
assert.throws(() => parseVerticalSliceResponse({ ...response, reconciliation_result: { ...contractMock, family_member_id: crypto.randomUUID() } }, familyId), ApiError);
assert.throws(() => parseVerticalSliceResponse({ ...response, current_intake_states: [{ ...response.current_intake_states[0], intake_status: 'TAKING' }] }, familyId), ApiError);
console.log('API response checks passed: family isolation, local mock mode, and safe intake defaults.');
