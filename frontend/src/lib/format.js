// Display helpers, using German formats (2,49 €, 10.10.2026) to match the receipts.

/** 2.49 → "2,49 €" */
export function formatMoney(amount, currency = "EUR") {
  if (amount === null || amount === undefined) return "–";
  return new Intl.NumberFormat("de-DE", { style: "currency", currency }).format(amount);
}

/** 1234.5 → "1.235 €" (no cents; for chart axes) */
export function formatMoneyShort(amount, currency = "EUR") {
  return new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

/** "2026-10" → "October 2026" */
export function formatMonth(month) {
  return new Date(`${month}-01T00:00:00`).toLocaleDateString("en-GB", { month: "long", year: "numeric" });
}

/** "2026-10" → "Oct 26" (for chart axes) */
export function formatMonthShort(month) {
  return new Date(`${month}-01T00:00:00`).toLocaleDateString("en-GB", { month: "short", year: "2-digit" });
}

/** Today's month as "YYYY-MM". */
export function currentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

/** shiftMonth("2026-01", -1) → "2025-12" */
export function shiftMonth(month, delta) {
  const [year, mon] = month.split("-").map(Number);
  const date = new Date(year, mon - 1 + delta, 1);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

/** "2026-10-10" → "10.10.2026" */
export function formatDate(isoDate) {
  if (!isoDate) return "–";
  // Add a time so the date isn't shifted by the browser's time zone.
  return new Date(`${isoDate}T00:00:00`).toLocaleDateString("de-DE");
}

/**
 * Parse a number typed by the user. Accepts "2,49" and "2.49".
 * Returns null for empty or invalid input.
 */
export function parseNumber(value) {
  if (value === null || value === undefined || String(value).trim() === "") return null;
  const number = Number(String(value).trim().replace(",", "."));
  return Number.isFinite(number) ? number : null;
}
