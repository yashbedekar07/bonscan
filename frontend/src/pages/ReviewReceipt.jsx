import { useEffect, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";
import { apiGet, apiPost } from "../lib/api";
import { formatMoney, parseNumber } from "../lib/format";
import Alert from "../components/Alert";

// Same tolerance as the backend check (in EUR).
const TOTAL_TOLERANCE = 0.05;
const DEFAULT_CATEGORY = "Other";

// Numbers are kept as strings while editing, so "2," doesn't jump around as you type.
const toInput = (value) => (value === null || value === undefined ? "" : String(value));

function newItem(fields = {}) {
  return {
    key: crypto.randomUUID(), // stable React key for each row
    name: "",
    quantity: "1",
    unit_price: "",
    total_price: "",
    category: DEFAULT_CATEGORY,
    ...fields,
  };
}

/** Turn the AI draft into editable form state. */
function draftToForm(draft) {
  return {
    store_name: draft.store_name ?? "",
    purchase_date: draft.purchase_date ?? "",
    total_amount: toInput(draft.total_amount),
    vat_amount: toInput(draft.vat_amount),
    currency: draft.currency || "EUR",
  };
}

function draftToItems(draft) {
  return draft.items.map((item) =>
    newItem({
      name: item.name,
      quantity: toInput(item.quantity),
      unit_price: toInput(item.unit_price),
      total_price: toInput(item.total_price),
      category: item.suggested_category,
    })
  );
}

const inputClass =
  "block w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/30";
const cellInputClass =
  "block w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/30";

function ReviewReceipt() {
  const navigate = useNavigate();
  const location = useLocation();
  const scan = location.state?.scan; // result of POST /api/receipts/extract

  const [form, setForm] = useState(() => (scan ? draftToForm(scan.draft) : null));
  const [items, setItems] = useState(() => (scan ? draftToItems(scan.draft) : []));
  const [categories, setCategories] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet("/api/categories")
      .then(setCategories)
      .catch((err) => setError(`Couldn't load categories: ${err.message}`));
  }, []);

  // Opened directly or after a page reload: there's nothing to review.
  if (!scan) return <Navigate to="/scan" replace />;

  // ---------- Live total check ----------
  const itemsSum = items.reduce((sum, item) => sum + (parseNumber(item.total_price) ?? 0), 0);
  const total = parseNumber(form.total_amount);
  const difference = total === null ? null : itemsSum - total;
  const totalsMatch = difference !== null && Math.abs(difference) <= TOTAL_TOLERANCE;

  // ---------- Editing ----------
  function updateForm(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function updateItem(key, field, value) {
    setItems((prev) =>
      prev.map((item) => {
        if (item.key !== key) return item;
        const updated = { ...item, [field]: value };

        // Changing quantity or unit price recalculates the line total.
        if (field === "quantity" || field === "unit_price") {
          const quantity = parseNumber(updated.quantity);
          const unitPrice = parseNumber(updated.unit_price);
          if (quantity !== null && unitPrice !== null) {
            updated.total_price = (Math.round(quantity * unitPrice * 100) / 100).toFixed(2);
          }
        }
        return updated;
      })
    );
  }

  const addItem = () => setItems((prev) => [...prev, newItem()]);
  const removeItem = (key) => setItems((prev) => prev.filter((item) => item.key !== key));

  // ---------- Saving ----------
  function validate() {
    if (!form.store_name.trim()) return "Please enter the store name.";
    if (!form.purchase_date) return "Please enter the purchase date.";
    if (total === null) return "Please enter the total amount.";
    if (form.vat_amount.trim() && parseNumber(form.vat_amount) === null) return "VAT must be a number.";
    if (items.length === 0) return "Add at least one item.";
    for (const [index, item] of items.entries()) {
      const row = `Item ${index + 1}`;
      if (!item.name.trim()) return `${row}: please enter a name.`;
      if (!(parseNumber(item.quantity) > 0)) return `${row}: quantity must be greater than 0.`;
      if (parseNumber(item.total_price) === null) return `${row}: please enter a price.`;
    }
    return "";
  }

  async function handleSave() {
    const problem = validate();
    setError(problem);
    if (problem) return;

    const payload = {
      store_name: form.store_name.trim(),
      purchase_date: form.purchase_date,
      total_amount: total,
      vat_amount: parseNumber(form.vat_amount),
      currency: form.currency,
      image_path: scan.image_path,
      raw_ai_json: scan.raw_ai_json,
      items: items.map((item) => ({
        name: item.name.trim(),
        quantity: parseNumber(item.quantity),
        unit_price: parseNumber(item.unit_price),
        total_price: parseNumber(item.total_price),
        category: item.category,
      })),
    };

    setSaving(true);
    try {
      const { id } = await apiPost("/api/receipts", payload);
      navigate(`/receipts/${id}`, { replace: true });
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  // ---------- UI ----------
  return (
    <>
      <h1 className="text-2xl font-semibold text-slate-800">Check your receipt</h1>
      <p className="mt-1 text-slate-500">The AI filled this in. Fix anything that looks wrong, then save.</p>

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        {/* Left: the photo, so you can compare while editing */}
        <div className="lg:col-span-2">
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white lg:sticky lg:top-6">
            {scan.image_url ? (
              <a href={scan.image_url} target="_blank" rel="noreferrer" title="Open full size">
                <img src={scan.image_url} alt="Scanned receipt" className="mx-auto max-h-[80vh] object-contain" />
              </a>
            ) : (
              <p className="p-6 text-center text-slate-500">Image not available.</p>
            )}
          </div>
        </div>

        {/* Right: the editable form */}
        {/* min-w-0 lets the wide items table scroll instead of stretching the page */}
        <div className="min-w-0 space-y-6 lg:col-span-3">
          {scan.warnings.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              <p className="font-medium">Please double-check:</p>
              <ul className="mt-1 list-disc pl-5">
                {scan.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Receipt details */}
          <section className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 sm:grid-cols-2">
            <label className="block sm:col-span-2">
              <span className="text-sm font-medium text-slate-700">Store</span>
              <input
                className={`mt-1 ${inputClass}`}
                value={form.store_name}
                onChange={(e) => updateForm("store_name", e.target.value)}
                placeholder="e.g. REWE"
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Date</span>
              <input
                type="date"
                className={`mt-1 ${inputClass}`}
                value={form.purchase_date}
                onChange={(e) => updateForm("purchase_date", e.target.value)}
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Total ({form.currency})</span>
              <input
                inputMode="decimal"
                className={`mt-1 ${inputClass}`}
                value={form.total_amount}
                onChange={(e) => updateForm("total_amount", e.target.value)}
                placeholder="0,00"
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">VAT / MwSt ({form.currency})</span>
              <input
                inputMode="decimal"
                className={`mt-1 ${inputClass}`}
                value={form.vat_amount}
                onChange={(e) => updateForm("vat_amount", e.target.value)}
                placeholder="optional"
              />
            </label>
          </section>

          {/* Items */}
          <section className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-slate-800">Items ({items.length})</h2>
              <button
                onClick={addItem}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100"
              >
                + Add item
              </button>
            </div>

            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="pb-2 pr-2 font-medium">Name</th>
                    <th className="w-16 pb-2 pr-2 font-medium">Qty</th>
                    <th className="w-24 pb-2 pr-2 font-medium">Unit €</th>
                    <th className="w-24 pb-2 pr-2 font-medium">Total €</th>
                    <th className="w-44 pb-2 pr-2 font-medium">Category</th>
                    <th className="w-8 pb-2" />
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.key} className="align-top">
                      <td className="py-1 pr-2">
                        <input
                          className={cellInputClass}
                          value={item.name}
                          onChange={(e) => updateItem(item.key, "name", e.target.value)}
                          aria-label="Item name"
                        />
                      </td>
                      <td className="py-1 pr-2">
                        <input
                          inputMode="decimal"
                          className={cellInputClass}
                          value={item.quantity}
                          onChange={(e) => updateItem(item.key, "quantity", e.target.value)}
                          aria-label="Quantity"
                        />
                      </td>
                      <td className="py-1 pr-2">
                        <input
                          inputMode="decimal"
                          className={cellInputClass}
                          value={item.unit_price}
                          onChange={(e) => updateItem(item.key, "unit_price", e.target.value)}
                          aria-label="Unit price"
                        />
                      </td>
                      <td className="py-1 pr-2">
                        <input
                          inputMode="decimal"
                          className={`${cellInputClass} ${parseNumber(item.total_price) < 0 ? "text-red-600" : ""}`}
                          value={item.total_price}
                          onChange={(e) => updateItem(item.key, "total_price", e.target.value)}
                          aria-label="Total price"
                        />
                      </td>
                      <td className="py-1 pr-2">
                        <select
                          className={cellInputClass}
                          value={item.category}
                          onChange={(e) => updateItem(item.key, "category", e.target.value)}
                          aria-label="Category"
                        >
                          {/* Keep the current value selectable even before categories load. */}
                          {categories.length === 0 && <option value={item.category}>{item.category}</option>}
                          {categories.map((category) => (
                            <option key={category.id} value={category.name}>
                              {category.icon} {category.name}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="py-1 text-right">
                        <button
                          onClick={() => removeItem(item.key)}
                          className="rounded-md px-2 py-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
                          aria-label={`Delete ${item.name || "item"}`}
                          title="Delete item"
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Live sum check */}
            <div
              className={`mt-4 rounded-lg px-4 py-3 text-sm ${
                totalsMatch ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-700"
              }`}
            >
              Items add up to <strong>{formatMoney(itemsSum, form.currency)}</strong>
              {total !== null && (
                <>
                  {" "}· receipt total <strong>{formatMoney(total, form.currency)}</strong>
                  {totalsMatch ? " ✓" : ` · difference ${formatMoney(difference, form.currency)}`}
                </>
              )}
            </div>
          </section>

          {error && <Alert>{error}</Alert>}

          <div className="flex justify-end gap-3">
            <button
              onClick={() => navigate("/scan")}
              disabled={saving}
              className="rounded-lg border border-slate-300 px-4 py-2.5 font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-60"
            >
              Discard
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="rounded-lg bg-emerald-600 px-6 py-2.5 font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? "Saving…" : "Save receipt"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

export default ReviewReceipt;
