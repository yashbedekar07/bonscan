import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { apiDelete, apiGet } from "../lib/api";
import { formatDate, formatMoney } from "../lib/format";
import Alert from "../components/Alert";

/** Show quantities without pointless decimals: 1 → "1", 0.512 → "0.512". */
const formatQuantity = (quantity) => String(Number(quantity));

function ReceiptDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [receipt, setReceipt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    apiGet(`/api/receipts/${id}`)
      .then(setReceipt)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  async function handleDelete() {
    if (!window.confirm("Delete this receipt and its photo? This can't be undone.")) return;

    setDeleting(true);
    try {
      await apiDelete(`/api/receipts/${id}`);
      navigate("/receipts", { replace: true });
    } catch (err) {
      setError(err.message);
      setDeleting(false);
    }
  }

  if (loading) return <p className="text-slate-400">Loading receipt…</p>;

  if (!receipt) {
    return (
      <div className="mx-auto max-w-xl space-y-4">
        <Alert>{error || "Receipt not found."}</Alert>
        <Link to="/receipts" className="text-sm font-medium text-emerald-700 hover:underline">
          ← Back to my receipts
        </Link>
      </div>
    );
  }

  return (
    <>
      <Link to="/receipts" className="text-sm font-medium text-emerald-700 hover:underline">
        ← My receipts
      </Link>

      <div className="mt-4 grid gap-6 lg:grid-cols-5">
        {/* Photo */}
        <div className="lg:col-span-2">
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white lg:sticky lg:top-6">
            {receipt.image_url ? (
              <a href={receipt.image_url} target="_blank" rel="noreferrer" title="Open full size">
                <img src={receipt.image_url} alt="Receipt" className="mx-auto max-h-[80vh] object-contain" />
              </a>
            ) : receipt.has_image ? (
              <p className="p-6 text-center text-slate-500">The photo couldn't be loaded. Please reload the page.</p>
            ) : (
              // Receipts without a photo, e.g. the generated demo data.
              <div className="flex flex-col items-center gap-2 px-6 py-12 text-center text-slate-500">
                <span className="text-4xl" aria-hidden="true">🧾</span>
                <p className="font-medium text-slate-600">No image (demo data)</p>
                <p className="text-sm">This receipt was saved without a photo.</p>
              </div>
            )}
          </div>
        </div>

        {/* Details */}
        {/* min-w-0 lets the wide items table scroll instead of stretching the page */}
        <div className="min-w-0 space-y-6 lg:col-span-3">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold text-slate-800">{receipt.store_name || "Unknown store"}</h1>
              <p className="mt-1 text-slate-500">{formatDate(receipt.purchase_date)}</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-semibold text-slate-800">
                {formatMoney(receipt.total_amount, receipt.currency)}
              </p>
              {receipt.vat_amount !== null && (
                <p className="text-sm text-slate-500">
                  incl. {formatMoney(receipt.vat_amount, receipt.currency)} VAT
                </p>
              )}
            </div>
          </div>

          {error && <Alert>{error}</Alert>}

          <section className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Item</th>
                  <th className="px-4 py-3 font-medium">Category</th>
                  <th className="px-4 py-3 text-right font-medium">Qty</th>
                  <th className="px-4 py-3 text-right font-medium">Price</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {receipt.items.map((item) => (
                  <tr key={item.id}>
                    <td className="px-4 py-2.5 text-slate-800">{item.name}</td>
                    <td className="px-4 py-2.5 text-slate-600">
                      {item.category_icon} {item.category_name ?? "–"}
                    </td>
                    <td className="px-4 py-2.5 text-right text-slate-600">{formatQuantity(item.quantity)}</td>
                    <td
                      className={`px-4 py-2.5 text-right font-medium ${
                        item.total_price < 0 ? "text-red-600" : "text-slate-800"
                      }`}
                    >
                      {formatMoney(item.total_price, receipt.currency)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <div className="flex justify-end">
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="rounded-lg border border-red-200 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-60"
            >
              {deleting ? "Deleting…" : "Delete receipt"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

export default ReceiptDetail;
