import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AXIS_COLOR, GRID_COLOR, SERIES_COLORS } from "../../lib/chartColors";
import { currentMonth, formatMoney, formatMoneyShort, formatMonth, formatMonthShort } from "../../lib/format";
import ChartTooltip from "./ChartTooltip";

const COLOR = SERIES_COLORS[0];

/**
 * Add the dashed "projected" series to the trend:
 * last complete month (actual) → this month (end-of-month projection) → next month (forecast).
 */
function withProjection(trend, forecast) {
  if (!forecast || trend.length < 2) return trend;
  const rows = trend.map((row) => ({ ...row }));
  const current = rows.at(-1);
  rows.at(-2).projected = rows.at(-2).total; // start the dashed line where the solid line is real
  current.projected = forecast.projected_total;
  if (forecast.next_month.forecast !== null) {
    rows.push({ month: forecast.next_month.month, total: null, projected: forecast.next_month.forecast });
  }
  return rows;
}

/** Line chart of total spending per month. Clicking a point opens that month. */
function TrendChart({ trend, forecast, selectedMonth, onSelectMonth }) {
  const data = withProjection(trend, forecast);

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{ top: 8, right: 12, bottom: 0, left: 0 }}
          onClick={(state) => {
            // Future months (the forecast) can't be opened.
            const month = state?.activeLabel;
            if (month && month <= currentMonth()) onSelectMonth(month);
          }}
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
                rows={(payload) => {
                  const row = payload[0].payload;
                  const rows = [];
                  if (row.total !== null && row.total !== undefined) {
                    rows.push({ label: row.month === currentMonth() ? "Spent so far" : "Spent", value: formatMoney(row.total) });
                  }
                  if (row.projected !== undefined && row.month >= currentMonth()) {
                    rows.push({ label: row.month === currentMonth() ? "Projected" : "Forecast", value: formatMoney(row.projected) });
                  }
                  if (row.receipt_count !== undefined) rows.push({ label: "Receipts", value: row.receipt_count });
                  return rows;
                }}
              />
            }
          />
          {forecast && <Legend iconType="plainline" wrapperStyle={{ fontSize: 12 }} />}
          <Line
            name="Spent"
            type="linear" // straight lines: there are no values between months
            dataKey="total"
            stroke={COLOR}
            strokeWidth={2}
            isAnimationActive={false}
            // Bigger dot for the month that's selected at the top.
            dot={({ cx, cy, payload, key }) =>
              payload.total === null ? null : (
                <circle
                  key={key}
                  cx={cx}
                  cy={cy}
                  r={payload.month === selectedMonth ? 6 : 4}
                  fill={payload.month === selectedMonth ? COLOR : "#ffffff"}
                  stroke={COLOR}
                  strokeWidth={2}
                />
              )
            }
            activeDot={{ r: 6, stroke: "#ffffff", strokeWidth: 2, cursor: "pointer" }}
          />
          {forecast && (
            <Line
              name="Projected"
              type="linear"
              dataKey="projected"
              stroke={COLOR}
              strokeWidth={2}
              strokeDasharray="6 4"
              dot={{ r: 4, fill: "#ffffff", stroke: COLOR, strokeWidth: 2, strokeDasharray: "0" }} // solid dots
              activeDot={false}
              isAnimationActive={false}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default TrendChart;
