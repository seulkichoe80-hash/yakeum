const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { contractMock } = require('../src/mock.ts');
const {
 getCurrentIntakeState,
 replaceFamilyIntakeStates,
 verifyCurrentIntake,
} = require('../src/currentIntakeUi.ts');
const { groupNormalizationAttention } = require('../src/presentation.ts');
const {
 initialResultViewState,
 mockItemsForFamily,
 resultViewReducer,
} = require('../src/resultView.ts');

const tests = [];
function test(name, run) { tests.push({ name, run }); }

const familyA = '00000000-0000-4000-8000-000000000001';
const familyB = '00000000-0000-4000-8000-000000000002';
const mockItems = contractMock.items.map((item, index) => ({ ...item, id: `source-${index}` }));
const source = fs.readFileSync(path.resolve(__dirname, '../src/main.tsx'), 'utf8');

test('1. initial result view is EMPTY and not an automatic Mock', () => {
 assert.deepEqual(initialResultViewState(familyA), { memberId: familyA, mode: 'EMPTY' });
});

test('2. a completed Backend analysis is the only Backend result mode', () => {
 const state = resultViewReducer(initialResultViewState(familyA), {
  type: 'backendSucceeded', memberId: familyA,
 });
 assert.equal(state.mode, 'BACKEND');
});

test('3. moving to family 2 clears family 1 result visibility', () => {
 const backend = { memberId: familyA, mode: 'BACKEND' };
 assert.deepEqual(resultViewReducer(backend, { type: 'memberChanged', memberId: familyB }), {
  memberId: familyB, mode: 'EMPTY',
 });
});

test('4. returning to family 1 remains EMPTY instead of automatic Mock', () => {
 const familyBState = { memberId: familyB, mode: 'EMPTY' };
 const returned = resultViewReducer(familyBState, { type: 'memberChanged', memberId: familyA });
 assert.equal(returned.mode, 'EMPTY');
});

test('5. empty result view provides re-analysis guidance', () => {
 assert.match(source, /표시할 비교 결과가 없습니다/);
 assert.match(source, /자료 분석하기/);
 assert.match(source, /실제 자료가 저장되거나 복구된 것처럼 표시하지 않습니다/);
});

test('6. Mock is shown only after explicit selection and is scoped to the selected family', () => {
 const state = resultViewReducer(initialResultViewState(familyB), {
  type: 'mockSelected', memberId: familyB,
 });
 const items = mockItemsForFamily(mockItems, familyB);
 assert.equal(state.mode, 'MOCK');
 assert.ok(items.every(item =>
  (!item.previous_record || item.previous_record.family_member_id === familyB)
  && (!item.current_record || item.current_record.family_member_id === familyB)));
});

test('7. previous and current normalization warnings are grouped separately', () => {
 const unmatched = {
  status: 'UNMATCHED', record: null,
  match: { source: null, official_id: null, match_method: null },
  warnings: [{ code: 'W', message: '원본 경고', field: null }], errors: [],
 };
 const partial = { ...unmatched, status: 'PARTIAL' };
 const groups = groupNormalizationAttention({ previous: [unmatched], current: [partial] });
 assert.deepEqual(groups.map(group => [group.source, group.title, group.results.length]), [
  ['previous', '이전 자료의 공식 제품정보 미확인', 1],
  ['current', '현재 자료의 공식 제품정보 미확인', 1],
 ]);
});

test('8. normalization groups render collapsed details that can be expanded', () => {
 assert.match(source, /<details className="normalization-group"/);
 assert.doesNotMatch(source, /<details[^>]*\sopen(?:=|\s|>)/);
 assert.match(source, /<summary>/);
});

test('9. grouping preserves the original normalization result and warning data', () => {
 const result = {
  status: 'UNMATCHED', record: null,
  match: { source: 'LOCAL_MOCK', official_id: null, match_method: null },
  warnings: [{ code: 'NO_MATCH', message: '원본 경고 유지', field: 'drug_code' }], errors: [],
 };
 const before = structuredClone(result);
 const groups = groupNormalizationAttention({ previous: [result], current: [] });
 assert.strictEqual(groups[0].results[0], result);
 assert.deepEqual(result, before);
});

test('10. existing Current Intake confirmation semantics remain unchanged', () => {
 const items = mockItemsForFamily(mockItems, familyA);
 const pending = items.find(item => item.status === 'NEEDS_CONFIRMATION');
 const recordId = pending.previous_record.record_id;
 const initial = replaceFamilyIntakeStates({}, familyA, items);
 assert.deepEqual(
  [getCurrentIntakeState(initial, familyA, recordId).intake_status,
   getCurrentIntakeState(initial, familyA, recordId).verification_status],
  ['UNKNOWN', 'PENDING'],
 );
 const verified = verifyCurrentIntake(initial, familyA, recordId, 'TAKING');
 assert.deepEqual(
  [getCurrentIntakeState(verified, familyA, recordId).intake_status,
   getCurrentIntakeState(verified, familyA, recordId).verification_status],
  ['TAKING', 'USER_VERIFIED'],
 );
});

for (const { name, run } of tests) {
 run();
 console.log(`ok - ${name}`);
}
console.log(`Current Intake UX checks passed: ${tests.length} cases.`);
