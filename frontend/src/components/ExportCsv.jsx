import { useState } from "react";
import { apiDownload } from "../lib/api";

/** Local date as YYYY-MM-DD (toISOString would use UTC and can be a day off). */
function isoDate(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

/** Date range + "Export CSV" button. The file opens directly in German Excel. */
function ExportCsv() {
  const today = new Date();
  const [from, setFrom] = useState(isoDate(new Date(today.getFullYear(), today.getMonth(), 1)));
  const [to, setTo] = useState(isoDate(today));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleExport(event) {
    event.preventDefault();
    if (!from || !to || from > to) {
      setError("Choose a start date on or before the end date.");
      return;
    }
    setError("");
    setBusy(true);
    try {
      await apiDownload(`/api/export/csv?from=${from}&to=${to}`, `bonscan_${from}_${to}.csv`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const inputClass =
    "mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/30";

  return (
    <form onSubmit={handleExport} className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
      <h2 className="font-semibold text-slate-800">Export to Excel (CSV)</h2>
      <p className="text-sm text-slate-500">One row per item, formatted for German Excel.</p>

      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
        <label className="block text-sm font-medium text-slate-700">
          From
          <input type="date" value={from} max={to} onChange={(e) => setFrom(e.target.value)} className={inputClass} />
        </label>
        <label className="block text-sm font-medium text-slate-700">
          To
          <input type="date" value={to} min={from} onChange={(e) => setTo(e.target.value)} className={inputClass} />
        </label>
        <button
          type="submit"
          disabled={busy}
          className="col-span-2 rounded-lg border border-emerald-600 px-4 py-2 font-medium text-emerald-700 hover:bg-emerald-50 disabled:opacity-60 sm:col-span-1"
        >
          {busy ? "Exporting…" : "⬇ Export CSV"}
        </button>
      </div>
      {error && <p className="mt-2 text-sm text-red-600" role="alert">{error}</p>}
    </form>
  );
}

export default ExportCsv;
