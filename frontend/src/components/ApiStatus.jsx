import { useEffect, useState } from "react";
import { API_URL } from "../lib/api";

/** Small indicator that pings /api/health to show whether the backend is up. */
function ApiStatus() {
  // "loading" until the health check finishes, then "ok" or "error".
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    fetch(`${API_URL}/api/health`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => setStatus(data.status === "ok" ? "ok" : "error"))
      .catch(() => setStatus("error"));
  }, []);

  if (status === "loading") {
    return <span className="text-slate-400">Checking API…</span>;
  }
  if (status === "ok") {
    return <span className="text-emerald-700">API connected ✅</span>;
  }
  return <span className="text-red-600">API not reachable ❌</span>;
}

export default ApiStatus;
