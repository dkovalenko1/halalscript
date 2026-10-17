// Western 0-9 <-> Eastern Arabic ٠-٩ (U+0660..U+0669).

const ARABIC_ZERO = 0x0660;

export function toArabicDigits(text: string): string {
  return text.replace(/[0-9]/g, (d) => String.fromCharCode(ARABIC_ZERO + Number(d)));
}

export function toWesternDigits(text: string): string {
  return text.replace(/[٠-٩]/g, (d) => String(d.charCodeAt(0) - ARABIC_ZERO));
}

/** A run of digits of either script around a position in a line, as [start, end). */
export function numberAround(lineText: string, offset: number): [number, number] | undefined {
  const isDigit = (c: string | undefined) => c !== undefined && /[0-9٠-٩]/.test(c);
  let start = offset;
  let end = offset;
  while (isDigit(lineText[start - 1])) {
    start--;
  }
  while (isDigit(lineText[end])) {
    end++;
  }
  return start < end ? [start, end] : undefined;
}
