// UI input checks only: no medication state or medical judgement.
export function fileError(name: string, size: number, isExcel: boolean): string | null {
 if (size === 0) return '내용이 없는 파일입니다. 다른 파일을 선택해 주세요.';
 if (size > 10 * 1024 * 1024) return '10MB 이하 파일을 선택해 주세요.';
 const supported = isExcel ? /\.(xlsx|xls)$/i.test(name) : /\.(png|jpe?g|webp)$/i.test(name);
 return supported ? null : '지원하지 않는 파일 형식입니다. 안내된 형식의 파일을 선택해 주세요.';
}
export function reviewError(product: string, strength: string, unit: string): string | null {
 if (!product.trim()) return '제품명을 입력해 주세요.';
 if (strength === '' && unit.trim()) return '단위를 입력했다면 함량도 입력해 주세요.';
 // Keep Decimal as text: reject negative/exponent/non-finite values without float conversion.
 if (strength !== '' && !/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(strength)) return '함량은 0 이상의 소수로 입력해 주세요.';
 if (strength !== '' && !unit.trim()) return '함량을 입력했다면 단위도 입력해 주세요.';
 return null;
}
