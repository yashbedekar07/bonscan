import { useEffect, useState } from "react";
import { Link } from "react-router";
import { apiGet } from "../lib/api";
import { formatDate, formatMoney } from "../lib/format";
import Alert from "../components/Alert";
import ExportCsv from "../components/ExportCsv";

function Receipts() {
  const [receipts, setReceipts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet("/api/receipts")
      .then(setReceipts)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-800">My receipts</h1>
        <Link
          to="/scan"
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
        >
          + Scan receipt
        </Link>
      </div>

      <div className="mt-6">
        <ExportCsv />
      </div>

      <div className="mt-6">
        {loading && <p className="text-slate-400">Loading receipts…</p>}
        {error && <Alert>Couldn't load receipts: {error}</Alert>}

        {!loading && !error && receipts.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
            <p className="text-4xl" aria-hidden="true">🧾</p>
            <p className="mt-3 font-medium text-slate-700">No receipts yet</p>
            <p className="mt-1 text-sm text-slate-500">Scan your first receipt to start tracking.</p>
          </div>
        )}

        {receipts.length > 0 && (
          <ul className="divide-y divide-slate-200 overflow-hidden rounded-2xl border border-slate-200 bg-white">
            {receipts.map((receipt) => (
              <li key={receipt.id}>
                <Link
                  to={`/receipts/${receipt.id}`}
                  className="flex items-center justify-between gap-4 px-5 py-4 hover:bg-slate-50"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium text-slate-800">{receipt.store_name || "Unknown store"}</p>
                    <p className="text-sm text-slate-500">
                      {formatDate(receipt.purchase_date)} · {receipt.item_count}{" "}
                      {receipt.item_count === 1 ? "item" : "items"}
                    </p>
                  </div>
                  <span className="shrink-0 font-semibold text-slate-800">
                    {formatMoney(receipt.total_amount, receipt.currency)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default Receipts;
