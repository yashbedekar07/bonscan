import { useEffect, useState } from "react";
import { API_URL } from "../lib/api";

/**
 * Small indicator that pings /api/health: shows whether the backend is up
 * and whether its .env is complete.
 */
function ApiStatus() {
  const [health, setHealth] = useState(null); // response of /api/health
  const [status, setStatus] = useState("loading"); // "loading" | "ok" | "error"

  useEffect(() => {
    fetch(`${API_URL}/api/health`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setHealth(data);
        setStatus(data.status === "ok" ? "ok" : "error");
      })
      .catch(() => setStatus("error"));
  }, []);

  if (status === "loading") {
    return <span className="text-slate-400">Checking API…</span>;
  }
  if (status === "error") {
    return <span className="text-red-600">API not reachable ❌ (is the backend running on {API_URL}?)</span>;
  }

  const missing = [
    !health.supabase_configured && "Supabase",
    !health.gemini_configured && "Gemini",
  ].filter(Boolean);

  if (missing.length > 0) {
    return (
      <span className="text-amber-700">
        API connected ⚠️ backend/.env is missing: {missing.join(", ")}
      </span>
    );
  }
  return <span className="text-emerald-700">API connected ✅</span>;
}

export default ApiStatus;
