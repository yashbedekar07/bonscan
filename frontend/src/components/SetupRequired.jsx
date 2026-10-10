/** Shown instead of the app when frontend/.env is missing required settings. */
function SetupRequired({ missing }) {
  return (
    <main className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="w-full max-w-lg rounded-2xl border border-amber-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-bold text-emerald-600">BonScan</h1>
        <h2 className="mt-4 text-lg font-semibold text-slate-800">Setup needed</h2>
        <p className="mt-2 text-slate-600">
          These settings are missing from <code className="rounded bg-slate-100 px-1">frontend/.env</code>:
        </p>
        <ul className="mt-3 list-disc pl-6 font-mono text-sm text-slate-800">
          {missing.map((name) => (
            <li key={name}>{name}</li>
          ))}
        </ul>
        <p className="mt-4 text-sm text-slate-600">
          Copy the values from Supabase → Project Settings → API Keys, then restart{" "}
          <code className="rounded bg-slate-100 px-1">npm run dev</code> (Vite only reads .env on start).
        </p>
      </div>
    </main>
  );
}

export default SetupRequired;
