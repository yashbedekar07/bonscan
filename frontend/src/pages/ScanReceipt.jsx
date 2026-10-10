import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { apiUpload } from "../lib/api";
import Alert from "../components/Alert";
import Spinner from "../components/Spinner";

const MAX_FILE_BYTES = 10 * 1024 * 1024; // must match the backend limit
// HEIC isn't listed on purpose: iPhones then convert their photos to JPEG automatically.
const ACCEPTED_TYPES = "image/jpeg,image/png,image/webp";

/** Rough client-side check; the backend does the real validation. */
function checkFile(file) {
  if (/\.(heic|heif)$/i.test(file.name) || /image\/hei[cf]/.test(file.type)) {
    return "HEIC photos aren't supported. Please use JPG, PNG or WEBP.";
  }
  if (!file.type.startsWith("image/")) return "Please choose an image (JPG, PNG or WEBP).";
  if (file.size > MAX_FILE_BYTES) return "The image is larger than 10 MB. Please use a smaller photo.";
  return "";
}

function ScanReceipt() {
  const navigate = useNavigate();

  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [previewFailed, setPreviewFailed] = useState(false); // browser can't display the file
  const [dragActive, setDragActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Free the preview's memory when it changes or the page closes.
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  function selectFile(newFile) {
    if (!newFile) return;
    const problem = checkFile(newFile);
    setError(problem);
    if (problem) return;

    setFile(newFile);
    setPreviewFailed(false);
    setPreviewUrl(URL.createObjectURL(newFile));
  }

  function handleDrop(event) {
    event.preventDefault();
    setDragActive(false);
    selectFile(event.dataTransfer.files[0]);
  }

  function reset() {
    setFile(null);
    setPreviewUrl("");
    setError("");
  }

  async function handleScan() {
    setError("");
    setLoading(true);
    try {
      const scan = await apiUpload("/api/receipts/extract", file);
      // Hand the AI draft over to the review page.
      navigate("/scan/review", { state: { scan } });
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="text-2xl font-semibold text-slate-800">Scan a receipt</h1>
      <p className="mt-1 text-slate-500">
        Take a photo of the whole receipt, flat and well lit. The AI reads the items for you.
      </p>

      <div className="mt-6 space-y-4">
        {error && <Alert>{error}</Alert>}

        {!file ? (
          <>
            {/* Drop zone: the whole area is a label, so clicking it opens the file picker. */}
            <label
              htmlFor="receipt-file"
              onDragOver={(e) => {
                e.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={handleDrop}
              className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-14 text-center transition ${
                dragActive
                  ? "border-emerald-500 bg-emerald-50"
                  : "border-slate-300 bg-white hover:border-emerald-400"
              }`}
            >
              <span className="text-5xl" aria-hidden="true">🧾</span>
              <span className="mt-3 font-medium text-slate-700">
                Drag your receipt here or <span className="text-emerald-700 underline">choose a file</span>
              </span>
              <span className="mt-1 text-sm text-slate-500">JPG, PNG or WEBP · max 10 MB</span>
            </label>
            <input
              id="receipt-file"
              type="file"
              accept={ACCEPTED_TYPES}
              className="sr-only"
              onChange={(e) => selectFile(e.target.files[0])}
            />

            {/* Camera button: only shown on small screens (phones). */}
            <label
              htmlFor="receipt-camera"
              className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-3 font-medium text-white hover:bg-emerald-700 sm:hidden"
            >
              📷 Take a photo
            </label>
            <input
              id="receipt-camera"
              type="file"
              accept={ACCEPTED_TYPES}
              capture="environment"
              className="sr-only"
              onChange={(e) => selectFile(e.target.files[0])}
            />
          </>
        ) : (
          <>
            <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white">
              {previewFailed ? (
                <div className="px-6 py-14 text-center text-slate-500">
                  <p className="font-medium text-slate-700">{file.name}</p>
                  <p className="mt-1 text-sm">No preview for this format, but it can still be read.</p>
                </div>
              ) : (
                <img
                  src={previewUrl}
                  alt="Receipt preview"
                  onError={() => setPreviewFailed(true)}
                  className="mx-auto max-h-[60vh] object-contain"
                />
              )}

              {/* Overlay while the AI works. */}
              {loading && (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-white/85 text-emerald-700">
                  <Spinner className="h-8 w-8" />
                  <p className="font-medium">Reading your receipt…</p>
                  <p className="text-sm text-slate-500">This usually takes 5–20 seconds.</p>
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <button
                onClick={reset}
                disabled={loading}
                className="flex-1 rounded-lg border border-slate-300 px-4 py-2.5 font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-60"
              >
                Choose another
              </button>
              <button
                onClick={handleScan}
                disabled={loading}
                className="flex-1 rounded-lg bg-emerald-600 px-4 py-2.5 font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Reading…" : "Read receipt"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default ScanReceipt;
