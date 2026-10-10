import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { categoryColor, OTHER_COLOR } from "../../lib/chartColors";
import { formatMoney } from "../../lib/format";
import ChartTooltip from "./ChartTooltip";

const EVERYTHING_ELSE = "Everything else";

/** Combine categories without their own colour into one grey slice. */
function toSlices(categories) {
  const slices = [];
  const rest = { name: EVERYTHING_ELSE, icon: "", amount: 0, percent: 0, color: OTHER_COLOR, members: [] };
  for (const category of categories) {
    const color = categoryColor(category.name);
    if (color) {
      slices.push({ ...category, color });
    } else {
      rest.amount += category.amount;
      rest.percent += category.percent;
      rest.members.push(category.name);
    }
  }
  if (rest.members.length === 1) {
    // Only one leftover category: show it under its own name, still in grey.
    const only = categories.find((c) => c.name === rest.members[0]);
    slices.push({ ...only, color: OTHER_COLOR });
  } else if (rest.members.length > 1) {
    slices.push(rest);
  }
  return slices;
}

/** Donut chart of spending per category, with a list that doubles as the legend and table view. */
function CategoryDonut({ categories }) {
  const slices = toSlices(categories);
  const total = slices.reduce((sum, slice) => sum + slice.amount, 0);

  return (
    <div className="space-y-4">
      <div className="relative mx-auto h-52 max-w-xs">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={slices}
              dataKey="amount"
              nameKey="name"
              innerRadius="62%"
              outerRadius="95%"
              startAngle={90}
              endAngle={-270}
              stroke="#ffffff" // 2px gap between slices
              strokeWidth={2}
              isAnimationActive={false}
            >
              {slices.map((slice) => (
                <Cell key={slice.name} fill={slice.color} />
              ))}
            </Pie>
            <Tooltip
              content={
                <ChartTooltip
                  rows={(payload) => {
                    const slice = payload[0].payload;
                    return [
                      {
                        color: slice.color,
                        label: slice.members?.length ? `${slice.name} (${slice.members.join(", ")})` : slice.name,
                        value: `${formatMoney(slice.amount)} · ${slice.percent.toFixed(1).replace(".", ",")} %`,
                      },
                    ];
                  }}
                />
              }
            />
          </PieChart>
        </ResponsiveContainer>
        {/* Total in the middle of the donut */}
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          {/* Sum of item prices; can differ by a few cents from the receipt totals. */}
          <span className="text-xs text-slate-500">Items total</span>
          <span className="text-lg font-semibold text-slate-900">{formatMoney(total)}</span>
        </div>
      </div>

      {/* Legend + values: identity never depends on colour alone */}
      <ul className="space-y-2 text-sm">
        {slices.map((slice) => (
          <li key={slice.name} className="flex items-center gap-2">
            <span className="h-3 w-3 shrink-0 rounded-sm" style={{ background: slice.color }} aria-hidden="true" />
            <span className="min-w-0 flex-1 truncate text-slate-700">
              {slice.icon} {slice.name}
            </span>
            <span className="tabular-nums text-slate-500">{slice.percent.toFixed(1).replace(".", ",")} %</span>
            <span className="w-20 text-right font-medium tabular-nums text-slate-800">{formatMoney(slice.amount)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default CategoryDonut;
