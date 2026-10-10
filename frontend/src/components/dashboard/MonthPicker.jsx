import { currentMonth, formatMonth, shiftMonth } from "../../lib/format";

/** "‹ October 2026 ›" switcher. Can't go past the current month. */
function MonthPicker({ month, onChange }) {
  const isCurrent = month >= currentMonth();
  const buttonClass =
    "rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40";

  return (
    <div className="flex items-center gap-2">
      <button onClick={() => onChange(shiftMonth(month, -1))} className={buttonClass} aria-label="Previous month">
        ‹
      </button>
      <span className="min-w-36 text-center font-medium text-slate-800" aria-live="polite">
        {formatMonth(month)}
      </span>
      <button
        onClick={() => onChange(shiftMonth(month, 1))}
        disabled={isCurrent}
        className={buttonClass}
        aria-label="Next month"
      >
        ›
      </button>
      {!isCurrent && (
        <button
          onClick={() => onChange(currentMonth())}
          className="ml-1 text-sm font-medium text-emerald-700 hover:underline"
        >
          This month
        </button>
      )}
    </div>
  );
}

export default MonthPicker;
