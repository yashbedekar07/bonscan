// Display helpers, using German formats (2,49 €, 10.10.2026) to match the receipts.

/** 2.49 → "2,49 €" */
export function formatMoney(amount, currency = "EUR") {
  if (amount === null || amount === undefined) return "–";
  return new Intl.NumberFormat("de-DE", { style: "currency", currency }).format(amount);
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
