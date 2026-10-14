export * from './types';
import { contractMock } from './mock';
import type { Item, ReconciliationResult } from './types';

export function toItems(result: ReconciliationResult, prefix = 'backend'): Item[] {
 return result.items.map((item, index): Item => {
  const recordId = item.current_record?.record_id ?? item.previous_record?.record_id ?? `item-${index}`;
  return { ...item, id: `${prefix}-${recordId}-${index}` };
 });
}

export const mockResult = { ...contractMock, items: toItems(contractMock, 'mock') };
