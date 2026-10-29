import type { NormalizationResult, NormalizationStatus, ResultBatches, Status } from './types';

export const reconciliationDescriptions: Record<Status, string> = {
 MAINTAINED: '기록상 변경이 발견되지 않음',
 NEW: '현재 자료에서 새로 확인됨',
 DOSE_CHANGED: '함량 또는 투약정보 변경',
 NEEDS_CONFIRMATION: '최신 자료에서 확인되지 않음',
};

export const normalizationLabels: Record<NormalizationStatus, string> = {
 MATCHED: '공식 제품정보 확인',
 PARTIAL: '제품정보 일부 확인 필요',
 UNMATCHED: '공식 제품정보 미확인',
 FAILED: '자료 처리 실패',
};

export const localMockNotice = '가상 의약품 매칭이며 실제 식약처 조회가 수행되지 않았습니다.';

export type NormalizationAttentionGroup = {
 source: 'previous' | 'current';
 title: string;
 results: NormalizationResult[];
};

export function groupNormalizationAttention(batches: ResultBatches): NormalizationAttentionGroup[] {
 return ([
  ['previous', '이전 자료의 공식 제품정보 미확인'],
  ['current', '현재 자료의 공식 제품정보 미확인'],
 ] as const).map(([source, title]) => ({
  source,
  title,
  results: batches[source].filter(result => result.status === 'PARTIAL' || result.status === 'UNMATCHED'),
 })).filter(group => group.results.length > 0);
}
