import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import AppLayout from "./components/AppLayout";
import Login from "./pages/Login";
import SignUp from "./pages/SignUp";
import Dashboard from "./pages/Dashboard";
import ScanReceipt from "./pages/ScanReceipt";
import ReviewReceipt from "./pages/ReviewReceipt";
import Receipts from "./pages/Receipts";
import ReceiptDetail from "./pages/ReceiptDetail";

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<SignUp />} />

          {/* Logged-in pages share the header/navigation from AppLayout. */}
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/scan" element={<ScanReceipt />} />
            <Route path="/scan/review" element={<ReviewReceipt />} />
            <Route path="/receipts" element={<Receipts />} />
            <Route path="/receipts/:id" element={<ReceiptDetail />} />
          </Route>

          {/* Anything else (including "/") goes to the dashboard,
              which in turn sends logged-out users to /login. */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
