import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router";
import { supabase } from "../lib/supabase";
import { useAuth } from "../context/AuthContext";
import AuthLayout from "../components/AuthLayout";
import FormField from "../components/FormField";
import SubmitButton from "../components/SubmitButton";
import Alert from "../components/Alert";

// Supabase's default minimum password length.
const MIN_PASSWORD_LENGTH = 6;

function SignUp() {
  const { session } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  // Already logged in? Go straight to the dashboard.
  if (session) return <Navigate to="/dashboard" replace />;

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (password !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }

    setLoading(true);
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      // Where the confirmation email link sends the user back to.
      options: { emailRedirectTo: `${window.location.origin}/dashboard` },
    });
    setLoading(false);

    if (error) {
      setError(error.message);
      return;
    }

    if (data.session) {
      // Email confirmation is turned off in Supabase: the user is logged in right away.
      navigate("/dashboard", { replace: true });
    } else {
      // Email confirmation is on: the user must click the link in their inbox first.
      setMessage(`Almost done! We sent a confirmation link to ${email}.`);
      setPassword("");
      setConfirmPassword("");
    }
  }

  return (
    <AuthLayout
      title="Create an account"
      subtitle="Start tracking your supermarket spending."
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-emerald-700 hover:underline">
            Log in
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <Alert>{error}</Alert>}
        {message && <Alert type="success">{message}</Alert>}

        <FormField
          label="Email"
          id="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={loading}
        />
        <FormField
          label={`Password (min. ${MIN_PASSWORD_LENGTH} characters)`}
          id="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={MIN_PASSWORD_LENGTH}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={loading}
        />
        <FormField
          label="Confirm password"
          id="confirm-password"
          type="password"
          autoComplete="new-password"
          required
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          disabled={loading}
        />

        <SubmitButton loading={loading} loadingText="Creating account…">
          Sign up
        </SubmitButton>
      </form>
    </AuthLayout>
  );
}

export default SignUp;
