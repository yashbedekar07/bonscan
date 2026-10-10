// Icons per alert kind, so cards are recognisable without relying on colour.
const KIND_ICON = { budget: "🎯", category_spike: "📈", price_increase: "🏷️" };

const TYPE_STYLE = {
  warning: "border-amber-200 bg-amber-50 text-amber-900",
  info: "border-sky-200 bg-sky-50 text-sky-900",
};

/** Alert messages from /api/insights/alerts shown as cards. */
function InsightsList({ alerts }) {
  if (alerts.length === 0) {
    return (
      <p className="rounded-xl bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
        Nothing unusual this month. 👍
      </p>
    );
  }

  return (
    <ul className="grid gap-3 md:grid-cols-2">
      {alerts.map((alert, index) => (
        <li key={index} className={`flex gap-3 rounded-xl border px-4 py-3 text-sm ${TYPE_STYLE[alert.type]}`}>
          <span className="text-lg leading-5" aria-hidden="true">
            {KIND_ICON[alert.kind] ?? "ℹ️"}
          </span>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide opacity-75">
              {alert.type === "warning" ? "Warning" : "Info"}
            </p>
            <p className="mt-0.5">{alert.message}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}

export default InsightsList;
