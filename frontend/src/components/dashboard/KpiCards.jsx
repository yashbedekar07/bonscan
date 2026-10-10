import { formatMoney } from "../../lib/format";
import { Skeleton } from "./ChartCard";

function Card({ label, value, children }) {
  return (
    <div className="min-w-0 rounded-2xl border border-slate-200 bg-white p-4">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 truncate text-2xl font-semibold text-slate-900">{value}</p>
      {children && <div className="mt-1 text-sm">{children}</div>}
    </div>
  );
}

/** Spending change vs last month. Arrow + words, so it doesn't rely on colour alone. */
function Change({ percent }) {
  if (percent === null) return <span className="text-slate-500">No spending last month</span>;
  if (percent === 0) return <span className="text-slate-500">Same as last month</span>;

  // For expenses, spending more is the "bad" direction.
  const up = percent > 0;
  return (
    <span className={up ? "text-red-700" : "text-emerald-700"}>
      {up ? "↑" : "↓"} {Math.abs(percent).toLocaleString("de-DE")} % {up ? "more" : "less"} than last month
    </span>
  );
}

/** The four headline numbers at the top of the dashboard. */
function KpiCards({ summary, loading }) {
  if (loading || !summary) {
    return (
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Card label="Total spent" value={formatMoney(summary.total_spent)}>
        <Change percent={summary.change_percent} />
      </Card>
      <Card label="Receipts" value={summary.receipt_count} />
      <Card
        label="Average per receipt"
        value={summary.average_per_receipt === null ? "–" : formatMoney(summary.average_per_receipt)}
      />
      <Card label="Top store" value={summary.top_store?.store ?? "–"}>
        {summary.top_store && (
          <span className="text-slate-500">
            {summary.top_store.visits} {summary.top_store.visits === 1 ? "visit" : "visits"} ·{" "}
            {formatMoney(summary.top_store.amount)}
          </span>
        )}
      </Card>
    </div>
  );
}

export default KpiCards;
