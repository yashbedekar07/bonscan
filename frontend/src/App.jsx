import { useEffect, useState } from "react";

// Base URL of the FastAPI backend, set in frontend/.env (see .env.example).
const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function App() {
  // "loading" until the health check finishes, then "ok" or "error".
  const [apiStatus, setApiStatus] = useState("loading");

  // Ping the backend once when the page loads.
  useEffect(() => {
    fetch(`${API_URL}/api/health`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => setApiStatus(data.status === "ok" ? "ok" : "error"))
      .catch(() => setApiStatus("error"));
  }, []);

  return (
    <main className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-sm border border-slate-200 p-8 text-center">
        <h1 className="text-4xl font-bold text-emerald-600">BonScan</h1>
        <p className="mt-3 text-slate-600">
          Snap your supermarket receipts and see where your money goes.
        </p>

        <div className="mt-8 text-sm font-medium">
          {apiStatus === "loading" && (
            <span className="text-slate-400">Checking API…</span>
          )}
          {apiStatus === "ok" && (
            <span className="text-emerald-700">API connected ✅</span>
          )}
          {apiStatus === "error" && (
            <span className="text-red-600">API not reachable ❌</span>
          )}
        </div>
      </div>
    </main>
  );
}

export default App;
