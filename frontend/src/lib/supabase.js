import { createClient } from "@supabase/supabase-js";

// Public Supabase settings from frontend/.env (see .env.example).
// The anon/publishable key is safe in the browser: Row Level Security protects the data.
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL?.trim();
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY?.trim();

// Names of required settings that are missing. main.jsx shows a setup screen
// instead of the app when this isn't empty.
export const missingConfig = [
  !supabaseUrl && "VITE_SUPABASE_URL",
  !supabaseAnonKey && "VITE_SUPABASE_ANON_KEY",
].filter(Boolean);

// One shared client for the whole app. It stores the session in localStorage
// and refreshes the access token automatically.
export const supabase = missingConfig.length === 0 ? createClient(supabaseUrl, supabaseAnonKey) : null;
