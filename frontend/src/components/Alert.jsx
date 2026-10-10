/** Coloured message box for errors ("error") and confirmations ("success"). */
function Alert({ type = "error", children }) {
  const styles =
    type === "success"
      ? "bg-emerald-50 text-emerald-800 border-emerald-200"
      : "bg-red-50 text-red-700 border-red-200";

  return (
    <div role="alert" className={`rounded-lg border px-3 py-2 text-sm ${styles}`}>
      {children}
    </div>
  );
}

export default Alert;
