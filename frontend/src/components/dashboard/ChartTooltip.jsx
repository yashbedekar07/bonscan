/**
 * Tooltip box for Recharts: a title line and one row per value.
 * `rows` turns Recharts' payload into [{ color, label, value }].
 */
function ChartTooltip({ active, payload, title, rows }) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-md">
      {title && <p className="font-medium text-slate-800">{title(payload)}</p>}
      {rows(payload).map((row) => (
        <p key={row.label} className="mt-0.5 flex items-center gap-2 text-slate-600">
          {row.color && <span className="h-2.5 w-2.5 rounded-full" style={{ background: row.color }} />}
          <span>{row.label}:</span>
          <span className="font-medium text-slate-800">{row.value}</span>
        </p>
      ))}
    </div>
  );
}

export default ChartTooltip;
