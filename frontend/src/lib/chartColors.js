// Chart colours, from a colour-blind-safe categorical palette (validated light-mode steps).
// The order matters: neighbouring colours stay distinguishable for colour-blind readers.
export const SERIES_COLORS = [
  "#2a78d6", // blue
  "#eb6834", // orange
  "#1baf7a", // aqua
  "#eda100", // yellow
  "#e87ba4", // magenta
  "#008300", // green
  "#4a3aa7", // violet
  "#e34948", // red
];

// Neutral grey for "everything else"; never used for a named series.
export const OTHER_COLOR = "#a8a69f";

// Chart chrome (axes, grid, labels).
export const GRID_COLOR = "#e1e0d9";
export const AXIS_COLOR = "#898781";

// Each category keeps the same colour in every month and every chart, no matter
// its rank. Only 8 colours are safe, so the rarest categories share the grey
// "Everything else" slice.
const CATEGORY_COLORS = {
  Groceries: SERIES_COLORS[0],
  "Drugstore & Hygiene": SERIES_COLORS[1],
  Household: SERIES_COLORS[2],
  "Drinks & Snacks": SERIES_COLORS[3],
  "Eating Out": SERIES_COLORS[4],
  "Deposit (Pfand)": SERIES_COLORS[5],
  Transport: SERIES_COLORS[6],
  Clothing: SERIES_COLORS[7],
};

/** Colour for a category, or null if it belongs in "Everything else". */
export function categoryColor(name) {
  return CATEGORY_COLORS[name] ?? null;
}
