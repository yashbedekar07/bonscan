import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AXIS_COLOR, GRID_COLOR, SERIES_COLORS } from "../../lib/chartColors";
import { formatMoney, formatMoneyShort, formatMonth, formatMonthShort } from "../../lib/format";
import ChartTooltip from "./ChartTooltip";

/** Line chart of total spending per month. Clicking a point opens that month. */
function TrendChart({ trend, selectedMonth, onSelectMonth }) {
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={trend}
          margin={{ top: 8, right: 12, bottom: 0, left: 0 }}
          onClick={(state) => state?.activeLabel && onSelectMonth(state.activeLabel)}
        >
          <CartesianGrid vertical={false} stroke={GRID_COLOR} />
          <XAxis
            dataKey="month"
            tickFormatter={formatMonthShort}
            tick={{ fill: AXIS_COLOR, fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: GRID_COLOR }}
            interval="preserveStartEnd"
            minTickGap={16}
          />
          <YAxis
            tickFormatter={(value) => formatMoneyShort(value)}
            tick={{ fill: AXIS_COLOR, fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            width={64}
          />
          <Tooltip
            cursor={{ stroke: AXIS_COLOR, strokeDasharray: "3 3" }}
            content={
              <ChartTooltip
                title={(payload) => formatMonth(payload[0].payload.month)}
                rows={(payload) => [
                  { label: "Spent", value: formatMoney(payload[0].payload.total) },
                  { label: "Receipts", value: payload[0].payload.receipt_count },
                ]}
              />
            }
          />
          <Line
            type="linear" // straight lines: there are no values between months
            dataKey="total"
            stroke={SERIES_COLORS[0]}
            strokeWidth={2}
            isAnimationActive={false}
            // Bigger dot for the month that's selected at the top.
            dot={({ cx, cy, payload, key }) => (
              <circle
                key={key}
                cx={cx}
                cy={cy}
                r={payload.month === selectedMonth ? 6 : 4}
                fill={payload.month === selectedMonth ? SERIES_COLORS[0] : "#ffffff"}
                stroke={SERIES_COLORS[0]}
                strokeWidth={2}
              />
            )}
            activeDot={{ r: 6, stroke: "#ffffff", strokeWidth: 2, cursor: "pointer" }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default TrendChart;
