export * from './types';
import { contractMock } from './mock';
import type { Item } from './types';
export const mockResult = { ...contractMock, items: contractMock.items.map((item, index): Item => ({ ...item, id: `mock-item-${index}` })) };
