import { useEffect, useState } from "react";
import { subscribeToWaking } from "../lib/serverWake";
import Spinner from "./Spinner";

/** Friendly message while the free-tier backend is starting up (see lib/serverWake.js). */
function WakeUpBanner() {
  const [waking, setWaking] = useState(false);
  useEffect(() => subscribeToWaking(setWaking), []);

  if (!waking) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed inset-x-0 top-3 z-50 mx-auto flex w-fit max-w-[calc(100%-2rem)] items-center gap-3 rounded-full border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900 shadow-md"
    >
      <Spinner className="h-4 w-4 shrink-0" />
      Waking up the server, this can take up to a minute…
    </div>
  );
}

export default WakeUpBanner;
