import { useEffect, useState } from "react";
import { apiDelete, apiGet, apiPut } from "../lib/api";
import { formatMoney, parseNumber } from "../lib/format";
import Alert from "../components/Alert";
import { Skeleton } from "../components/dashboard/ChartCard";

/** One category row: limit input, Save and Remove. */
function BudgetRow({ category, budget, onSaved, onRemoved }) {
  const [value, setValue] = useState(budget ? String(budget.monthly_limit).replace(".", ",") : "");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null); // {type: "ok" | "error", text}

  async function save(event) {
    event.preventDefault();
    const limit = parseNumber(value);
    if (limit === null || limit <= 0) {
      setMessage({ type: "error", text: "Enter an amount greater than 0." });
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const saved = await apiPut(`/api/budgets/${category.id}`, { monthly_limit: limit });
      onSaved(saved);
      setValue(String(saved.monthly_limit).replace(".", ","));
      setMessage({ type: "ok", text: "Saved ✓" });
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    setMessage(null);
    try {
      await apiDelete(`/api/budgets/${category.id}`);
      onRemoved(category.id);
      setValue("");
      setMessage({ type: "ok", text: "Removed" });
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="px-4 py-3 sm:px-5">
      <form onSubmit={save} className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <label htmlFor={`budget-${category.id}`} className="min-w-0 flex-1 basis-40 font-medium text-slate-700">
          <span aria-hidden="true">{category.icon}</span> {category.name}
          {budget && (
            <span className="block text-xs font-normal text-slate-500">
              Current limit: {formatMoney(budget.monthly_limit)} / month
            </span>
          )}
        </label>

        <div className="relative w-32">
          <input
            id={`budget-${category.id}`}
            inputMode="decimal"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="No limit"
            disabled={busy}
            className="block w-full rounded-lg border border-slate-300 py-2 pl-3 pr-7 text-right text-slate-900 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
          />
          <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-slate-400">€</span>
        </div>

        <button
          type="submit"
          disabled={busy}
          className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
        >
          Save
        </button>
        {budget && (
          <button
            type="button"
            onClick={remove}
            disabled={busy}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 disabled:opacity-60"
          >
            Remove
          </button>
        )}

        {message && (
          <p
            className={`w-full text-sm ${message.type === "ok" ? "text-emerald-700" : "text-red-600"}`}
            role={message.type === "error" ? "alert" : "status"}
          >
            {message.text}
          </p>
        )}
      </form>
    </li>
  );
}

function Budgets() {
  const [categories, setCategories] = useState([]);
  const [budgets, setBudgets] = useState({}); // category_id → budget
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([apiGet("/api/categories"), apiGet("/api/budgets")])
      .then(([categoryList, budgetList]) => {
        setCategories(categoryList);
        setBudgets(Object.fromEntries(budgetList.map((b) => [b.category_id, b])));
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const total = Object.values(budgets).reduce((sum, b) => sum + b.monthly_limit, 0);

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-semibold text-slate-800">Budgets</h1>
      <p className="mt-1 text-slate-500">
        Set a monthly limit for the categories you want to keep an eye on. Leave the others empty.
      </p>

      <div className="mt-6">
        {error && <Alert>Couldn't load budgets: {error}</Alert>}
        {loading && <Skeleton className="h-96" />}

        {!loading && !error && (
          <>
            <ul className="divide-y divide-slate-200 rounded-2xl border border-slate-200 bg-white">
              {categories.map((category) => (
                <BudgetRow
                  key={category.id}
                  category={category}
                  budget={budgets[category.id]}
                  onSaved={(saved) => setBudgets((prev) => ({ ...prev, [saved.category_id]: saved }))}
                  onRemoved={(id) =>
                    setBudgets((prev) => {
                      const next = { ...prev };
                      delete next[id];
                      return next;
                    })
                  }
                />
              ))}
            </ul>
            {total > 0 && (
              <p className="mt-3 text-right text-sm text-slate-600">
                Total of all budgets: <strong>{formatMoney(total)}</strong> / month
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default Budgets;
