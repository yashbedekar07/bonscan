import { Link } from "react-router";
import { formatMoney } from "../../lib/format";

// Status colours (reserved for status, never used for chart series). Each status
// also gets an icon and words, so it never relies on colour alone.
const STATUS = {
  ok: { bar: "#0ca30c", text: "text-emerald-700", icon: "✓", label: "On track" },
  warning: { bar: "#ec835a", text: "text-orange-700", icon: "⚠", label: "Almost used" },
  over: { bar: "#d03b3b", text: "text-red-700", icon: "✕", label: "Over budget" },
};

/** One progress bar per budgeted category: spent / limit for the selected month. */
function BudgetProgress({ progress, isCurrentMonth }) {
  if (progress.length === 0) {
    return (
      <div className="rounded-xl bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
        No budgets yet.{" "}
        <Link to="/budgets" className="font-medium text-emerald-700 hover:underline">
          Set monthly limits
        </Link>{" "}
        to track them here.
      </div>
    );
  }

  return (
    <ul className="space-y-4">
      {progress.map((b) => {
        const status = STATUS[b.status];
        const width = Math.min(b.percent, 100);
        return (
          <li key={b.category_id}>
            <div className="flex items-baseline justify-between gap-2 text-sm">
              <span className="min-w-0 truncate font-medium text-slate-700">
                {b.icon} {b.category_name}
              </span>
              <span className="shrink-0 tabular-nums text-slate-600">
                {formatMoney(b.spent)} / {formatMoney(b.monthly_limit)}
              </span>
            </div>
            <div
              className="mt-1.5 h-2.5 overflow-hidden rounded-full bg-slate-100"
              role="progressbar"
              aria-valuenow={Math.round(b.percent)}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`${b.category_name}: ${Math.round(b.percent)} % of budget used`}
            >
              <div className="h-full rounded-full" style={{ width: `${width}%`, background: status.bar }} />
            </div>
            <p className={`mt-1 text-xs ${status.text}`}>
              {status.icon} {status.label} · {b.percent.toLocaleString("de-DE")} %
              {b.status === "over" && ` · ${formatMoney(b.spent - b.monthly_limit)} over`}
              {isCurrentMonth && b.status !== "over" && b.projected > b.monthly_limit && (
                <span className="text-slate-500"> · on pace for {formatMoney(b.projected)}</span>
              )}
            </p>
          </li>
        );
      })}
    </ul>
  );
}

export default BudgetProgress;
