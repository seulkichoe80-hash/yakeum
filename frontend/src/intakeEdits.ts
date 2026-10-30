import type {CurrentIntakeState} from './types';
import type {IntakeChoice} from './currentIntakeUi';
// Display/edit semantics only. Never equate explicit UNKNOWN with unverified PENDING.
export function intakeSelectionsEqual(a:Record<string,CurrentIntakeState>,b:Record<string,CurrentIntakeState>):boolean{
 const ids=Object.keys(a);return ids.length===Object.keys(b).length&&ids.every(id=>b[id]?.intake_status===a[id].intake_status&&b[id]?.verification_status===a[id].verification_status);
}
export function changedIntakeChoices(baseline:CurrentIntakeState[],draft:Record<string,IntakeChoice>):Record<string,IntakeChoice>{
 return Object.fromEntries(Object.entries(draft).filter(([id,value])=>{const old=baseline.find(s=>s.medication_record_id===id);return !!old&&(old.verification_status!=='USER_VERIFIED'||old.intake_status!==value);}));
}
export function editIntakeChoice(baseline:CurrentIntakeState[],draft:Record<string,IntakeChoice>,id:string,value?:IntakeChoice){
 const next={...draft};if(value===undefined)delete next[id];else next[id]=value;return changedIntakeChoices(baseline,next);
}
// Only an explicit precondition/input rejection before a successful POST is a known failure.
// Network, timeout, 5xx, or a later GET failure leave the mutation outcome uncertain.
export function knownSaveRejection(error:unknown):boolean{
 return !!error&&typeof error==='object'&&'status' in error&&[400,403,404,409,413,415,422].includes(Number(error.status));
}
