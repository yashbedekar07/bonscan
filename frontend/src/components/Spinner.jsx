/** Small spinning circle for loading states. */
function Spinner({ className = "h-5 w-5" }) {
  return (
    <span
      className={`inline-block animate-spin rounded-full border-2 border-current border-t-transparent ${className}`}
      role="status"
      aria-label="Loading"
    />
  );
}

export default Spinner;
