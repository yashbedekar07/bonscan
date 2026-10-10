import { useState } from "react";
import { formatMoney } from "../../lib/format";

const VIEWS = [
  { key: "by_spend", label: "By spend" },
  { key: "by_count", label: "By count" },
];

/** Top items table with a "by spend / by count" switch. Clicking an item opens it in the price tracker. */
function TopItemsTable({ topItems, onSelectItem }) {
  const [view, setView] = useState("by_spend");
  const rows = topItems[view];

  return (
    <>
      <div className="inline-flex rounded-lg border border-slate-200 p-0.5 text-sm" role="tablist">
        {VIEWS.map((option) => (
          <button
            key={option.key}
            role="tab"
            aria-selected={view === option.key}
            onClick={() => setView(option.key)}
            className={`rounded-md px-3 py-1 font-medium ${
              view === option.key ? "bg-emerald-50 text-emerald-700" : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>

      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="w-8 py-2 font-medium">#</th>
              <th className="py-2 font-medium">Item</th>
              <th className="py-2 text-right font-medium">Bought</th>
              <th className="py-2 text-right font-medium">Spent</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((item, index) => (
              <tr key={item.name}>
                <td className="py-2 text-slate-400 tabular-nums">{index + 1}</td>
                <td className="py-2 pr-2">
                  <button
                    onClick={() => onSelectItem(item.name)}
                    className="text-left text-slate-800 [overflow-wrap:anywhere] hover:text-emerald-700 hover:underline"
                    title="Show price history"
                  >
                    {item.name}
                  </button>
                </td>
                <td className="py-2 text-right tabular-nums text-slate-600">{item.times_bought}×</td>
                <td className="py-2 text-right font-medium tabular-nums text-slate-800">
                  {formatMoney(item.total_spent)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export default TopItemsTable;
