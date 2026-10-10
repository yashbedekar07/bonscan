import { supabase } from "./supabase";

// Base URL of the FastAPI backend.
export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/**
 * GET a backend endpoint as the logged-in user.
 * Sends the Supabase access token as "Authorization: Bearer <token>".
 * Throws an Error with the backend's message if the request fails.
 */
export async function apiGet(path) {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers = session
    ? { Authorization: `Bearer ${session.access_token}` }
    : {};

  const res = await fetch(`${API_URL}${path}`, { headers });

  if (!res.ok) {
    // FastAPI errors look like {"detail": "..."}.
    let detail = null;
    try {
      detail = (await res.json()).detail;
    } catch {
      // Response wasn't JSON; fall back to the status code below.
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }

  return res.json();
}
