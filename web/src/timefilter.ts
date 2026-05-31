// Pure time-axis helpers. Kept free of Three.js / DOM so they can be unit-tested
// without executing main.ts's renderer side effects.

/** Parse the 4-digit year from an ISO date string ("2005-03-10" → 2005).
 *  Returns null for null/empty input, "0000…" placeholders, or unparseable text. */
export function parseYear(date: string | null): number | null {
  if (!date || date.startsWith('0000')) return null
  const y = parseInt(date.slice(0, 4), 10)
  return isNaN(y) ? null : y
}

/** True if a law's lifespan [born, death] overlaps the window [from, to].
 *  This is the real "which laws existed during this period?" test — not
 *  "which laws were born in this window".
 *
 *  born === null  → birth year unknown → treated as −∞ (born ≤ to always holds).
 *  death === null → never repealed (open-ended) → treated as +∞ (death ≥ from always holds). */
export function isInTimeWindow(
  born: number | null,
  death: number | null,
  from: number,
  to: number,
): boolean {
  const bornOk = born == null || born <= to
  const deathOk = death == null || death >= from
  return bornOk && deathOk
}
