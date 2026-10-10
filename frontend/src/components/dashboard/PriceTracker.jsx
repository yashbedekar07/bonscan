import { useEffect, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiGet } from "../../lib/api";
import { AXIS_COLOR, GRID_COLOR, SERIES_COLORS } from "../../lib/chartColors";
import { formatDate, formatMoney } from "../../lib/format";
import Alert from "../Alert";
import ChartTooltip from "./ChartTooltip";
import { NoData, Skeleton } from "./ChartCard";

const MAX_STORES = SERIES_COLORS.length;

const toTime = (isoDate) => new Date(`${isoDate}T00:00:00`).getTime();
const toIsoDate = (time) => {
  const d = new Date(time);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

/**
 * Turn [{date, store, price}] into Recharts rows: [{time, REWE: 1.09, Lidl: 0.99}, ...].
 * The x-axis is real time, so gaps between purchases are shown to scale.
 */
function toRows(points, stores) {
  const byTime = new Map();
  for (const point of points) {
    if (!stores.includes(point.store)) continue;
    const time = toTime(point.date);
    if (!byTime.has(time)) byTime.set(time, { time });
    byTime.get(time)[point.store] = point.price;
  }
  return [...byTime.values()].sort((a, b) => a.time - b.time);
}

/**
 * Search box + line chart of an item's price over time, one line per store.
 * `selectedItem` is {name} set from outside (a new object each click, so the same item can be re-picked).
 */
function PriceTracker({ selectedItem }) {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function search(item) {
    const text = item.trim();
    if (text.length < 2) {
      setError("Type at least 2 letters, e.g. “milch”.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      setResult(await apiGet(`/api/analytics/price-history?item=${encodeURIComponent(text)}`));
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  // Clicking an item in the top-items table searches for it here.
  useEffect(() => {
    if (selectedItem) {
      setQuery(selectedItem.name);
      search(selectedItem.name);
    }
  }, [selectedItem]);

  // Colour follows the store (alphabetical order), not how many points it has.
  const stores = result ? [...result.stores].slice(0, MAX_STORES).sort((a, b) => a.localeCompare(b)) : [];
  const rows = result ? toRows(result.points, stores) : [];

  // Latest price per store, shown under the chart (readable without the chart).
  const latest = stores.map((store) => {
    const last = result.points.filter((p) => p.store === store).at(-1);
    return { store, ...last };
  });

  return (
    <div className="space-y-4">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          search(query);
        }}
        className="flex gap-2"
      >
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search an item, e.g. milch, bananen, butter"
          className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-slate-900 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
          aria-label="Item to track"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
        >
          {loading ? "…" : "Show"}
        </button>
      </form>

      {error && <Alert>{error}</Alert>}
      {loading && <Skeleton className="h-64" />}

      {!loading && result && result.points.length === 0 && (
        <NoData>No purchases found for “{result.query}”. Try a shorter word, e.g. “milch” instead of “h-milch 1l”.</NoData>
      )}

      {!loading && result && result.points.length > 0 && (
        <>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
                <CartesianGrid vertical={false} stroke={GRID_COLOR} />
                <XAxis
                  dataKey="time"
                  type="number"
                  scale="time"
                  domain={["dataMin", "dataMax"]}
                  tickFormatter={(time) => formatDate(toIsoDate(time))}
                  tick={{ fill: AXIS_COLOR, fontSize: 12 }}
                  tickLine={false}
                  axisLine={{ stroke: GRID_COLOR }}
                  minTickGap={24}
                />
                <YAxis
                  tickFormatter={(value) => formatMoney(value)}
                  tick={{ fill: AXIS_COLOR, fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                  width={64}
                  domain={["auto", "auto"]}
                />
                <Tooltip
                  cursor={{ stroke: AXIS_COLOR, strokeDasharray: "3 3" }}
                  content={
                    <ChartTooltip
                      title={(payload) => formatDate(toIsoDate(payload[0].payload.time))}
                      rows={(payload) =>
                        payload.map((entry) => ({ color: entry.color, label: entry.name, value: formatMoney(entry.value) }))
                      }
                    />
                  }
                />
                {/* A legend only makes sense with two or more stores. */}
                {stores.length > 1 && <Legend iconType="plainline" wrapperStyle={{ fontSize: 12 }} />}
                {stores.map((store, index) => (
                  <Line
                    key={store}
                    dataKey={store}
                    name={store}
                    stroke={SERIES_COLORS[index]}
                    strokeWidth={2}
                    dot={{ r: 4, strokeWidth: 2, fill: "#ffffff" }}
                    activeDot={{ r: 6 }}
                    connectNulls // lines continue across days where only another store has a price
                    isAnimationActive={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          <ul className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-slate-600">
            {latest.map((entry) => (
              <li key={entry.store}>
                <span className="font-medium text-slate-800">{entry.store}</span>: last {formatMoney(entry.price)} on{" "}
                {formatDate(entry.date)}
              </li>
            ))}
          </ul>
          <p className="text-xs text-slate-500">
            Price per unit (or per kg). Includes: {result.matched_names.join(", ")}
          </p>
        </>
      )}
    </div>
  );
}

export default PriceTracker;
