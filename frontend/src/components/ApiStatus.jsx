import { useEffect, useState } from "react";
import { ensureServerAwake } from "../lib/serverWake";

/**
 * Small indicator that pings /api/health: shows whether the backend is up
 * (waiting for it to wake up if needed) and whether its settings are complete.
 */
function ApiStatus() {
  const [health, setHealth] = useState(null); // response of /api/health
  const [status, setStatus] = useState("loading"); // "loading" | "ok" | "error"

  useEffect(() => {
    ensureServerAwake({ force: true })
      .then((data) => {
        setHealth(data);
        setStatus(data?.status === "ok" ? "ok" : "error");
      })
      .catch(() => setStatus("error"));
  }, []);

  if (status === "loading") {
    return <span className="text-slate-400">Checking API…</span>;
  }
  if (status === "error") {
    return <span className="text-red-600">API not reachable ❌ Please try again in a minute.</span>;
  }

  const missing = [
    !health.supabase_configured && "Supabase",
    !health.gemini_configured && "Gemini",
  ].filter(Boolean);

  if (missing.length > 0) {
    return (
      <span className="text-amber-700">
        API connected ⚠️ server settings missing: {missing.join(", ")}
      </span>
    );
  }
  return <span className="text-emerald-700">API connected ✅</span>;
}

export default ApiStatus;
