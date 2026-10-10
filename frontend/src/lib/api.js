import { supabase } from "./supabase";

// Base URL of the FastAPI backend.
export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/** Turn a FastAPI error body into one readable sentence. */
function errorMessage(body, status) {
  const detail = body?.detail;
  if (typeof detail === "string") return detail;
  // Validation errors (422) are a list like [{loc: ["body", "store_name"], msg: "..."}].
  if (Array.isArray(detail)) {
    return detail
      .map((d) => `${d.loc.filter((part) => part !== "body").join(" → ")}: ${d.msg}`)
      .join("; ");
  }
  return `Request failed (${status})`;
}

/**
 * Call the backend as the logged-in user.
 * Sends the Supabase access token as "Authorization: Bearer <token>".
 * Throws an Error with a user-friendly message if the request fails.
 */
async function request(path, { method = "GET", json, formData, asBlob = false } = {}) {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers = {};
  if (session) headers.Authorization = `Bearer ${session.access_token}`;

  let body;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (formData) {
    body = formData; // the browser sets the multipart Content-Type itself
  }

  let res;
  try {
    res = await fetch(`${API_URL}${path}`, { method, headers, body });
  } catch {
    throw new Error("Can't reach the server. Is the backend running?");
  }

  if (!res.ok) {
    let errorBody = null;
    try {
      errorBody = await res.json();
    } catch {
      // Response wasn't JSON; errorMessage falls back to the status code.
    }
    throw new Error(errorMessage(errorBody, res.status));
  }

  if (res.status === 204) return null;
  return asBlob ? res.blob() : res.json();
}

export const apiGet = (path) => request(path);
export const apiPost = (path, json) => request(path, { method: "POST", json });
export const apiPut = (path, json) => request(path, { method: "PUT", json });
export const apiDelete = (path) => request(path, { method: "DELETE" });

/** Download a file from the backend (with the login token) and save it as `filename`. */
export async function apiDownload(path, filename) {
  const blob = await request(path, { asBlob: true });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

/** Upload a single file as multipart form data (field name "file"). */
export function apiUpload(path, file) {
  const formData = new FormData();
  formData.append("file", file);
  return request(path, { method: "POST", formData });
}
