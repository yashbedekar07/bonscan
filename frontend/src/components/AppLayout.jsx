import { NavLink, Outlet } from "react-router";
import { useAuth } from "../context/AuthContext";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/scan", label: "Scan receipt" },
  { to: "/receipts", label: "My receipts" },
];

/** Header with navigation, shown on every page for logged-in users. */
function AppLayout() {
  const { user, signOut } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200">
        <div className="mx-auto max-w-6xl flex flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 sm:px-6">
          <span className="text-2xl font-bold text-emerald-600">BonScan</span>

          <nav className="order-last flex w-full gap-1 sm:order-none sm:w-auto">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-1.5 text-sm font-medium ${
                    isActive ? "bg-emerald-50 text-emerald-700" : "text-slate-600 hover:bg-slate-100"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-3">
            <span className="hidden text-sm text-slate-500 md:inline">{user.email}</span>
            <button
              onClick={signOut}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              Log out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <Outlet />
      </main>
    </div>
  );
}

export default AppLayout;
