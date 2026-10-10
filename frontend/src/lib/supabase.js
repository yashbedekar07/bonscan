import { createClient } from "@supabase/supabase-js";
import { missingConfig, SUPABASE_ANON_KEY, SUPABASE_URL } from "./config";

// Re-exported for main.jsx, which shows a setup screen when settings are missing.
export { missingConfig };

// One shared client for the whole app. It stores the session in localStorage
// and refreshes the access token automatically.
export const supabase = missingConfig.length === 0 ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY) : null;
