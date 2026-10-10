import { formatMoney, formatMoneyShort, formatMonth } from "../../lib/format";

/** "At this pace you'll spend about 312 € this month" + next month's forecast. */
function ForecastCard({ forecast }) {
  const next = forecast.next_month;

  return (
    <div className="space-y-4">
      <div>
        <p className="text-lg text-slate-800">
          At this pace you'll spend about{" "}
          <strong className="text-slate-900">{formatMoneyShort(forecast.projected_total)}</strong> this month.
        </p>
        <p className="mt-1 text-sm text-slate-500">
          {formatMoney(forecast.spent_so_far)} spent in the first {forecast.days_passed} of {forecast.days_in_month}{" "}
          days.
          {forecast.days_passed <= 7 && " Early in the month, so this can still change a lot."}
        </p>
      </div>

      <div className="rounded-xl bg-slate-50 px-4 py-3">
        <p className="text-sm font-medium text-slate-700">{formatMonth(next.month)}</p>
        {next.forecast === null ? (
          <p className="mt-1 text-sm text-slate-500">{next.message}</p>
        ) : (
          <>
            <p className="mt-1 text-slate-800">
              Expected: about <strong>{formatMoneyShort(next.forecast)}</strong>
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Weighted average of{" "}
              {next.based_on
                .map((m) => `${formatMonth(m.month)} (${formatMoney(m.total)} × ${m.weight.toLocaleString("de-DE")})`)
                .join(", ")}
            </p>
          </>
        )}
      </div>
    </div>
  );
}

export default ForecastCard;
