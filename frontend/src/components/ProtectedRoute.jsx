import { Navigate, useLocation } from "react-router";
import { useAuth } from "../context/AuthContext";

/** Renders its children only for logged-in users; everyone else goes to /login. */
function ProtectedRoute({ children }) {
  const { session, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-400">
        Loading…
      </div>
    );
  }

  if (!session) {
    // Remember where the user wanted to go, so Login can send them back.
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return children;
}

export default ProtectedRoute;
