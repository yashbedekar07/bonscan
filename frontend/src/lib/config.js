// All frontend settings, from frontend/.env locally or the Vercel project settings in production.
// Nothing is hardcoded: if a value is missing, main.jsx shows a setup screen instead of the app.

/** URL of the FastAPI backend, without a trailing slash (e.g. https://bonscan-api.onrender.com). */
export const API_URL = (import.meta.env.VITE_API_URL ?? "").trim().replace(/\/+$/, "");

// Public Supabase settings. The anon/publishable key is safe in the browser:
// Row Level Security protects the data.
export const SUPABASE_URL = (import.meta.env.VITE_SUPABASE_URL ?? "").trim();
export const SUPABASE_ANON_KEY = (import.meta.env.VITE_SUPABASE_ANON_KEY ?? "").trim();

/** Names of required settings that are missing. */
export const missingConfig = [
  !API_URL && "VITE_API_URL",
  !SUPABASE_URL && "VITE_SUPABASE_URL",
  !SUPABASE_ANON_KEY && "VITE_SUPABASE_ANON_KEY",
].filter(Boolean);
