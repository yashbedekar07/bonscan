import ApiStatus from "./ApiStatus";

/** Centered card used by the Login and Sign up pages. */
function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <main className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <h1 className="text-center text-4xl font-bold text-emerald-600">BonScan</h1>

        <div className="mt-6 bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
          <h2 className="text-xl font-semibold text-slate-800">{title}</h2>
          {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
          <div className="mt-6">{children}</div>
        </div>

        {footer && <p className="mt-6 text-center text-sm text-slate-600">{footer}</p>}
        <p className="mt-2 text-center text-xs">
          <ApiStatus />
        </p>
      </div>
    </main>
  );
}

export default AuthLayout;
