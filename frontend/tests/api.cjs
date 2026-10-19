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

const {parseHiraV2Response}=require('../src/api.ts');
const v2={...response,response_version:'TASK_D_HIRA_V2',family_member_id:familyId,comparison:{executed:true,holds:[]},source_rows:[]};
assert.equal(parseHiraV2Response(v2,familyId),v2);
const source={ref:{side:'current',document_id:'virtual-doc',input_index:0},locator:null,raw_fields:{product_name:null},normalization_ref:'/review_results/current/0'};
const failed={status:'FAILED',record:null,match:{source:null,official_id:null,match_method:null},warnings:[],errors:[]};
const held={...v2,review_results:{previous:[],current:[failed]},source_rows:[source],comparison:{executed:false,holds:[{kind:'UNIDENTIFIED_FAILED_INPUT',message:'가상 실패',affected_refs:[source.ref]}]},reconciliation_result:null,current_intake_states:[]};
assert.equal(parseHiraV2Response(held,familyId),held);
for(const bad of [
 {...held,reconciliation_result:contractMock},
 {...held,current_intake_states:response.current_intake_states},
 {...held,comparison:{executed:false,holds:[]}},
 {...held,source_rows:[]},
 {...held,source_rows:[{...source,normalization_ref:'/review_results/current/9'}]},
 {...held,comparison:{executed:false,holds:[{...held.comparison.holds[0],affected_refs:[{...source.ref,document_id:'missing'}]}]}},
 {...v2,response_version:undefined},
 {...v2,reconciliation_result:null},
]) assert.throws(()=>parseHiraV2Response(bad,familyId),ApiError);
const zero={...v2,reconciliation_result:{...contractMock,items:[]},current_intake_states:[]};
assert.equal(parseHiraV2Response(zero,familyId).comparison.executed,true);
console.log('HIRA v2 checks passed: explicit version, held/empty distinction, source pointers and stale result rejection.');
