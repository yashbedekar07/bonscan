import { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

const AuthContext = createContext(null);

/** Keeps track of the Supabase session and shares it with the whole app. */
export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  // True until we know whether a session already exists (e.g. after a page reload).
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 1. Restore an existing session from localStorage.
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    });

    // 2. Stay in sync with logins, logouts and token refreshes.
    const { data } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
    });

    return () => data.subscription.unsubscribe();
  }, []);

  const value = {
    session,
    user: session?.user ?? null,
    loading,
    signOut: () => supabase.auth.signOut(),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** Access the current session/user from any component. */
export function useAuth() {
  return useContext(AuthContext);
}
