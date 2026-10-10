import { createClient } from "@supabase/supabase-js";

// Public Supabase settings from frontend/.env (see .env.example).
// The anon/publishable key is safe in the browser: Row Level Security protects the data.
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    "Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY. Copy frontend/.env.example to frontend/.env and fill them in, then restart `npm run dev`."
  );
}

// One shared client for the whole app. It stores the session in localStorage
// and refreshes the access token automatically.
export const supabase = createClient(supabaseUrl, supabaseAnonKey);
