import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import SetupRequired from "./components/SetupRequired.jsx";
import { missingConfig } from "./lib/supabase";
import "./index.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    {/* Without the Supabase settings nothing works, so explain instead of crashing. */}
    {missingConfig.length > 0 ? <SetupRequired missing={missingConfig} /> : <App />}
  </StrictMode>
);
