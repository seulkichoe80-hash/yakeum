const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const doc = fs.readFileSync(path.join(root, '../docs/API_CONTRACT.md'), 'utf8');
const section = doc.split('## 5. Frontend 개발용 ReconciliationResult Mock')[1];
const expected = JSON.parse(section.match(/```json\s*([\s\S]*?)\s*```/)[1]);
const source = fs.readFileSync(path.join(root, 'src/mock.ts'), 'utf8');
const actual = JSON.parse(source.split('export const contractMock: ReconciliationResult = ')[1].trim().replace(/;$/, ''));
assert.deepEqual(actual, expected, 'Frontend fixture must preserve the team contract including unconfirmed candidates');
const reasonCodes = {MAINTAINED:'SAME_INGREDIENT_SAME_STRENGTH', NEW:'NEW_RECORD', DOSE_CHANGED:'STRENGTH_OR_DOSAGE_CHANGED', NEEDS_CONFIRMATION:'NOT_FOUND_IN_LATEST_SOURCE'};
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
let recordCount = 0;
for (const item of actual.items) {
 assert.equal(item.reason_code, reasonCodes[item.status]);
 for (const record of [item.previous_record, item.current_record].filter(Boolean)) {
  recordCount++;
  assert.match(record.record_id, uuid);
  assert.equal(record.family_member_id, actual.family_member_id);
  assert.equal(typeof record.user_confirmed, 'boolean');
  assert.ok(record.drug_code === null || typeof record.drug_code === 'string');
  for (const key of ['dose_per_administration','administrations_per_day','duration_days','confidence']) assert.ok(record[key] === null || typeof record[key] === 'string', key);
  assert.ok(Array.isArray(record.ingredients));
  for (const ingredient of record.ingredients) assert.ok(ingredient.product_strength === null || typeof ingredient.product_strength === 'string');
 }
}
assert.equal(actual.items.find(i => i.status === 'NEW').current_record.user_confirmed, false);
assert.equal(actual.items.find(i => i.status === 'NEEDS_CONFIRMATION').current_record, null);
assert.equal(actual.items[0].current_record.drug_code, '000000001');
console.log(`Contract checks passed: ${actual.items.length} states, ${recordCount} records; false/null/leading zeros preserved.`);
