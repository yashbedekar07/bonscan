import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { apiGet } from "../lib/api";
import Alert from "../components/Alert";

function Dashboard() {
  const { user } = useAuth();

  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Load the categories from our backend (which checks the access token).
  useEffect(() => {
    apiGet("/api/categories")
      .then(setCategories)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <h1 className="text-2xl font-semibold text-slate-800">Welcome, {user.email}</h1>
      <p className="mt-1 text-slate-500">Your receipts will be sorted into these categories.</p>

      <section className="mt-8">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Categories
        </h2>

        {loading && <p className="mt-4 text-slate-400">Loading categories…</p>}
        {error && (
          <div className="mt-4">
            <Alert>Couldn't load categories: {error}</Alert>
          </div>
        )}

        {!loading && !error && (
          <ul className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5">
            {categories.map((category) => (
              <li
                key={category.id}
                className="flex flex-col items-center gap-2 rounded-xl border border-slate-200 bg-white p-4 text-center"
              >
                <span className="text-3xl" aria-hidden="true">
                  {category.icon}
                </span>
                <span className="text-sm font-medium text-slate-700">{category.name}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}

export default Dashboard;
