// Display only: never rewrite stored timestamps or source enums.
export function koreanSavedTime(value:string):string {
 if(!/(?:Z|[+-]\d{2}:\d{2})$/i.test(value))return value;
 const date=new Date(value);if(!Number.isFinite(date.getTime()))return '저장 시각 확인 필요';
 const parts=new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(date);
 const get=(name:string)=>parts.find(p=>p.type===name)!.value;
 return `${get('year')}.${get('month')}.${get('day')} ${get('hour')}:${get('minute')}`;
}
export function extractionSourceLabel(source:string='MOCK'):string {
 return source==='MOCK'?'가상 추출':source==='GEMINI'?'Gemini 추출':'추출 출처 확인 필요';
}
