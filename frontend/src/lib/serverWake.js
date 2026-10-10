import { API_URL } from "./config";

// The backend runs on Render's free tier, which sleeps after ~15 minutes without
// traffic. The first request then takes up to a minute while it starts again.
//
// Before talking to a server we haven't heard from in a while, we ping /api/health
// (and retry a few times) while showing "Waking up the server…". Only then is the
// real request sent, so uploads and saves are never sent twice.

const ASSUME_ASLEEP_AFTER_MS = 10 * 60 * 1000; // no contact for 10 minutes → it may be asleep
const SHOW_MESSAGE_AFTER_MS = 2500; // don't flash the message for normal, fast answers
const PING_TIMEOUT_MS = 20 * 1000;
const RETRY_DELAY_MS = 5 * 1000;
const MAX_ATTEMPTS = 4; // ≈ 4 × (20 s + 5 s) → gives up after about 1½ minutes

let lastContact = 0;
let wakeUp = null; // shared promise, so parallel requests wait for the same ping

// Components subscribe to know when to show the "waking up" message.
let waking = false;
const listeners = new Set();
function setWaking(value) {
  waking = value;
  listeners.forEach((listener) => listener(value));
}
export function subscribeToWaking(listener) {
  listeners.add(listener);
  listener(waking);
  return () => listeners.delete(listener);
}

/** Call after any successful answer from the backend. */
export function markServerAwake() {
  lastContact = Date.now();
}

/** Call when a request couldn't reach the server, so the next one checks first. */
export function markServerUnreachable() {
  lastContact = 0;
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function pingOnce() {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), PING_TIMEOUT_MS);
  try {
    const res = await fetch(`${API_URL}/api/health`, { signal: controller.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`); // e.g. 502/503 while Render starts the app
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Make sure the backend is awake. Resolves with /api/health's answer when it pinged
 * (or null if the server was recently reachable); throws if it never answers.
 * `force` always pings (used by the status indicator on the login page).
 */
export function ensureServerAwake({ force = false } = {}) {
  if (!force && Date.now() - lastContact < ASSUME_ASLEEP_AFTER_MS) return Promise.resolve(null);
  if (wakeUp) return wakeUp;

  wakeUp = (async () => {
    const showMessage = setTimeout(() => setWaking(true), SHOW_MESSAGE_AFTER_MS);
    try {
      for (let attempt = 1; ; attempt++) {
        try {
          const health = await pingOnce();
          markServerAwake();
          return health;
        } catch {
          if (attempt >= MAX_ATTEMPTS) {
            throw new Error("The server isn't responding right now. Please try again in a minute.");
          }
          setWaking(true);
          await sleep(RETRY_DELAY_MS);
        }
      }
    } finally {
      clearTimeout(showMessage);
      setWaking(false);
      wakeUp = null;
    }
  })();
  return wakeUp;
}
