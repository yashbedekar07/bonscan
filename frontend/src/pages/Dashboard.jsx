import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { apiGet } from "../lib/api";
import { currentMonth, formatMonth } from "../lib/format";
import Alert from "../components/Alert";
import ChartCard, { NoData, Skeleton } from "../components/dashboard/ChartCard";
import MonthPicker from "../components/dashboard/MonthPicker";
import KpiCards from "../components/dashboard/KpiCards";
import CategoryDonut from "../components/dashboard/CategoryDonut";
import StoreBars from "../components/dashboard/StoreBars";
import TrendChart from "../components/dashboard/TrendChart";
import TopItemsTable from "../components/dashboard/TopItemsTable";
import PriceTracker from "../components/dashboard/PriceTracker";

/** Shown when the user hasn't saved any receipts in the last 12 months. */
function EmptyDashboard() {
  return (
    <div className="mx-auto mt-6 max-w-md rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
      <p className="text-5xl" aria-hidden="true">📊</p>
      <h2 className="mt-4 text-lg font-semibold text-slate-800">No spending data yet</h2>
      <p className="mt-1 text-slate-500">
        Scan a supermarket receipt and your spending by category, store and month shows up here.
      </p>
      <Link
        to="/scan"
        className="mt-6 inline-block rounded-lg bg-emerald-600 px-5 py-2.5 font-medium text-white hover:bg-emerald-700"
      >
        Scan your first receipt
      </Link>
    </div>
  );
}

function Dashboard() {
  const [month, setMonth] = useState(currentMonth);

  // Data for the selected month (reloaded when the month changes).
  const [monthData, setMonthData] = useState(null); // {summary, categories, stores, topItems}
  const [monthLoading, setMonthLoading] = useState(true);
  // The 12-month trend doesn't depend on the selected month, so it's loaded once.
  const [trend, setTrend] = useState(null);
  const [error, setError] = useState("");

  const [selectedItem, setSelectedItem] = useState(null);
  const trackerRef = useRef(null);

  useEffect(() => {
    apiGet("/api/analytics/monthly-trend?months=12")
      .then(setTrend)
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    let cancelled = false; // ignore late answers if the month changed meanwhile
    setMonthLoading(true);
    setError("");

    const query = `month=${month}`;
    Promise.all([
      apiGet(`/api/analytics/summary?${query}`),
      apiGet(`/api/analytics/by-category?${query}`),
      apiGet(`/api/analytics/by-store?${query}`),
      apiGet(`/api/analytics/top-items?${query}&limit=10`),
    ])
      .then(([summary, categories, stores, topItems]) => {
        if (!cancelled) setMonthData({ summary, categories, stores, topItems });
      })
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setMonthLoading(false));

    return () => {
      cancelled = true;
    };
  }, [month]);

  function showPriceHistory(name) {
    setSelectedItem({ name }); // new object, so picking the same item again still searches
    trackerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const hasAnyData = trend?.some((m) => m.receipt_count > 0);
  const monthIsEmpty = !monthLoading && monthData?.summary.receipt_count === 0;
  const emptyText = `No receipts in ${formatMonth(month)}.`;

  // Nothing saved at all (once we know): show the big empty state instead of empty charts.
  if (trend && !hasAnyData && !monthLoading && monthData?.summary.receipt_count === 0) {
    return (
      <>
        <h1 className="text-2xl font-semibold text-slate-800">Your spending</h1>
        <EmptyDashboard />
      </>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-800">Your spending</h1>
        <MonthPicker month={month} onChange={setMonth} />
      </div>

      {error && <Alert>Couldn't load your dashboard: {error}</Alert>}

      <KpiCards summary={monthData?.summary} loading={monthLoading} />

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Spending by category" subtitle={`${formatMonth(month)} · based on item prices`}>
          {monthLoading ? (
            <Skeleton className="h-56" />
          ) : monthData?.categories.length ? (
            <CategoryDonut categories={monthData.categories} />
          ) : (
            <NoData>{emptyText}</NoData>
          )}
        </ChartCard>

        <ChartCard title="Spending by store" subtitle={formatMonth(month)}>
          {monthLoading ? (
            <Skeleton className="h-56" />
          ) : monthData?.stores.length ? (
            <StoreBars stores={monthData.stores} />
          ) : (
            <NoData>{emptyText}</NoData>
          )}
        </ChartCard>
      </div>

      <ChartCard title="Monthly trend" subtitle="Last 12 months · click a month to open it">
        {trend ? (
          <TrendChart trend={trend} selectedMonth={month} onSelectMonth={setMonth} />
        ) : (
          <Skeleton className="h-64" />
        )}
      </ChartCard>

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Top 10 items" subtitle={formatMonth(month)}>
          {monthLoading ? (
            <Skeleton className="h-72" />
          ) : monthIsEmpty || !monthData?.topItems.by_spend.length ? (
            <NoData>{emptyText}</NoData>
          ) : (
            <TopItemsTable topItems={monthData.topItems} onSelectItem={showPriceHistory} />
          )}
        </ChartCard>

        <div ref={trackerRef} className="min-w-0 scroll-mt-6">
          <ChartCard title="Price tracker" subtitle="How an item's price changed over time, per store">
            <PriceTracker selectedItem={selectedItem} />
          </ChartCard>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
