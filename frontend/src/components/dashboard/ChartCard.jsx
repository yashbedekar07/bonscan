/** White card with a title, used for every dashboard section. */
function ChartCard({ title, subtitle, action, className = "", children }) {
  return (
    <section className={`min-w-0 rounded-2xl border border-slate-200 bg-white p-4 sm:p-5 ${className}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="font-semibold text-slate-800">{title}</h2>
          {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
        </div>
        {action}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

/** Grey pulsing placeholder shown while data loads. */
export function Skeleton({ className = "h-48" }) {
  return <div className={`animate-pulse rounded-xl bg-slate-100 ${className}`} aria-hidden="true" />;
}

/** Message shown inside a card when there's nothing to chart. */
export function NoData({ children }) {
  return (
    <div className="flex h-40 items-center justify-center rounded-xl bg-slate-50 px-4 text-center text-sm text-slate-500">
      {children}
    </div>
  );
}

export default ChartCard;
