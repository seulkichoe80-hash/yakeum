const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { contractMock } = require('../src/mock.ts');
const {
 buildInitialFamilyIntakeStates,
 getCurrentIntakeState,
 intakeChoiceLabels,
 replaceFamilyIntakeStates,
 verifyCurrentIntake,
} = require('../src/currentIntakeUi.ts');
const { medicationSnapshot, medicationTimeline } = require('../src/timeline.ts');
const {
 localMockNotice,
 normalizationLabels,
 reconciliationDescriptions,
} = require('../src/presentation.ts');

const tests = [];
function test(name, run) { tests.push({ name, run }); }

const mockResult = {
 ...contractMock,
 items: contractMock.items.map((item, index) => ({ ...item, id: `test-${index}` })),
};
const familyA = mockResult.family_member_id;
const familyB = '00000000-0000-4000-8000-000000000002';
const pendingItem = mockResult.items.find(item => item.status === 'NEEDS_CONFIRMATION');
const pendingRecordId = pendingItem.previous_record.record_id;
const initialStore = replaceFamilyIntakeStates({}, familyA, mockResult.items);

test('1. initial state is UNKNOWN/PENDING', () => {
 const state = getCurrentIntakeState(initialStore, familyA, pendingRecordId);
 assert.equal(state.intake_status, 'UNKNOWN');
 assert.equal(state.verification_status, 'PENDING');
 assert.equal(state.verified_by, null);
 assert.equal(state.last_verified_at, null);
});

test('2. TAKING becomes USER_VERIFIED', () => {
 const next = verifyCurrentIntake(initialStore, familyA, pendingRecordId, 'TAKING', '2026-10-14T00:00:00Z');
 const state = getCurrentIntakeState(next, familyA, pendingRecordId);
 assert.equal(state.intake_status, 'TAKING');
 assert.equal(state.verification_status, 'USER_VERIFIED');
});

test('3. NOT_TAKING becomes USER_VERIFIED', () => {
 const next = verifyCurrentIntake(initialStore, familyA, pendingRecordId, 'NOT_TAKING');
 const state = getCurrentIntakeState(next, familyA, pendingRecordId);
 assert.equal(state.intake_status, 'NOT_TAKING');
 assert.equal(state.verification_status, 'USER_VERIFIED');
});

test('4. explicit UNKNOWN becomes USER_VERIFIED', () => {
 const next = verifyCurrentIntake(initialStore, familyA, pendingRecordId, 'UNKNOWN');
 const state = getCurrentIntakeState(next, familyA, pendingRecordId);
 assert.equal(state.intake_status, 'UNKNOWN');
 assert.equal(state.verification_status, 'USER_VERIFIED');
});

test('5. verification never mutates ReconciliationResult', () => {
 const before = structuredClone(mockResult);
 verifyCurrentIntake(initialStore, familyA, pendingRecordId, 'TAKING');
 assert.deepEqual(mockResult, before);
});

test('6. confirmation state is isolated by family', () => {
 const familyBItems = structuredClone(mockResult.items).map(item => ({
  ...item,
  previous_record: item.previous_record ? { ...item.previous_record, family_member_id: familyB } : null,
  current_record: item.current_record ? { ...item.current_record, family_member_id: familyB } : null,
 }));
 const withFamilyB = replaceFamilyIntakeStates(initialStore, familyB, familyBItems);
 const changed = verifyCurrentIntake(withFamilyB, familyA, pendingRecordId, 'TAKING');
 assert.equal(getCurrentIntakeState(changed, familyA, pendingRecordId).intake_status, 'TAKING');
 assert.equal(getCurrentIntakeState(changed, familyB, pendingRecordId).intake_status, 'UNKNOWN');
});

test('7. a fresh browser store resets verification', () => {
 const changed = verifyCurrentIntake(initialStore, familyA, pendingRecordId, 'TAKING');
 assert.equal(getCurrentIntakeState(changed, familyA, pendingRecordId).verification_status, 'USER_VERIFIED');
 const refreshed = { [familyA]: buildInitialFamilyIntakeStates(familyA, mockResult.items) };
 assert.equal(getCurrentIntakeState(refreshed, familyA, pendingRecordId).verification_status, 'PENDING');
});

test('8. timeline contains previous and current medication details', () => {
 const item = mockResult.items.find(candidate => candidate.status === 'DOSE_CHANGED');
 const timeline = medicationTimeline(item);
 assert.equal(timeline.previous.recordDate, '2026-08-10');
 assert.equal(timeline.current.recordDate, '2026-09-10');
 assert.equal(timeline.previous.productName, '가상제품C');
 assert.equal(timeline.current.ingredient, '가상성분C');
 assert.equal(timeline.status, 'DOSE_CHANGED');
});

test('9. absent records and unknown field values stay distinct from zero', () => {
 const snapshot = medicationSnapshot(null);
 assert.equal(snapshot.presence,'absent');
 for (const [key,value] of Object.entries(snapshot)) if(key!=='presence') assert.equal(value, '미확인');
 const record = structuredClone(pendingItem.previous_record);
 record.ingredients[0].product_strength = null;
 record.dose_per_administration = null;
 const partial = medicationSnapshot(record);
 assert.equal(partial.productStrength, '미확인');
 assert.equal(partial.dosePerAdministration, '미확인');
});

test('10. product strength and administration dose stay separate', () => {
 const item = mockResult.items.find(candidate => candidate.status === 'DOSE_CHANGED');
 const timeline = medicationTimeline(item);
 assert.equal(timeline.previous.productStrength, '100 mg');
 assert.equal(timeline.previous.dosePerAdministration, '1 정');
 assert.equal(timeline.current.productStrength, '200 mg');
 assert.equal(timeline.current.dosePerAdministration, '1 정');
});

test('11. FAILED, UNMATCHED and PARTIAL have distinct user copy', () => {
 assert.equal(normalizationLabels.FAILED, '자료 처리 실패');
 assert.equal(normalizationLabels.UNMATCHED, '공식 제품정보 미확인');
 assert.equal(normalizationLabels.PARTIAL, '제품정보 일부 확인 필요');
 assert.equal(new Set([normalizationLabels.FAILED, normalizationLabels.UNMATCHED, normalizationLabels.PARTIAL]).size, 3);
});

test('12. LOCAL_MOCK and medical-safe reconciliation copy are explicit', () => {
 assert.match(localMockNotice, /실제 식약처 조회가 수행되지 않았습니다/);
 assert.equal(reconciliationDescriptions.MAINTAINED, '기록상 변경이 발견되지 않음');
 assert.equal(reconciliationDescriptions.NEEDS_CONFIRMATION, '최신 자료에서 확인되지 않음');
 const source = fs.readFileSync(path.resolve(__dirname, '../src/main.tsx'), 'utf8');
 assert.match(source, /현재 브라우저에서만 유지되며 저장되지 않습니다/);
 assert.deepEqual(intakeChoiceLabels, {
  TAKING: '먹고 있음',
  NOT_TAKING: '먹지 않음',
  UNKNOWN: '잘 모르겠음',
 });
});

for (const { name, run } of tests) {
 run();
 console.log(`ok - ${name}`);
}
console.log(`Current Intake and timeline checks passed: ${tests.length} cases.`);
