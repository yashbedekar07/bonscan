import { Bar, BarChart, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AXIS_COLOR, SERIES_COLORS } from "../../lib/chartColors";
import { formatMoney } from "../../lib/format";
import ChartTooltip from "./ChartTooltip";

const MAX_STORES = 8;
const BAR_ROW_HEIGHT = 40;

/** Horizontal bars (store names stay readable on phones), one colour since it's one series. */
function StoreBars({ stores }) {
  const shown = stores.slice(0, MAX_STORES);

  return (
    <>
      <div style={{ height: shown.length * BAR_ROW_HEIGHT + 10 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={shown} layout="vertical" margin={{ top: 0, right: 72, bottom: 0, left: 0 }} barCategoryGap={8}>
            <XAxis type="number" hide />
            <YAxis
              type="category"
              dataKey="store"
              width={120}
              tickLine={false}
              axisLine={false}
              tick={{ fill: AXIS_COLOR, fontSize: 12 }}
              tickFormatter={(name) => (name.length > 16 ? `${name.slice(0, 15)}…` : name)}
            />
            <Tooltip
              cursor={{ fill: "#f1f5f9" }}
              content={
                <ChartTooltip
                  title={(payload) => payload[0].payload.store}
                  rows={(payload) => [
                    { label: "Spent", value: formatMoney(payload[0].payload.amount) },
                    { label: "Visits", value: payload[0].payload.visits },
                  ]}
                />
              }
            />
            <Bar dataKey="amount" fill={SERIES_COLORS[0]} radius={[0, 4, 4, 0]} isAnimationActive={false}>
              <LabelList
                dataKey="amount"
                position="right"
                formatter={(value) => formatMoney(value)}
                style={{ fill: "#475569", fontSize: 12 }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      {stores.length > MAX_STORES && (
        <p className="mt-2 text-xs text-slate-500">
          + {stores.length - MAX_STORES} more stores
        </p>
      )}
    </>
  );
}

export default StoreBars;
