import { useState } from "react";
import { api, ApiError, setAccessToken } from "../lib/api";

interface Props {
  onAuthenticated: () => void;
}

export function AuthForm({ onAuthenticated }: Props) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setWorking(true);
    try {
      if (mode === "register") {
        await api.register(email, password);
      }
      const tokens = await api.login(email, password);
      setAccessToken(tokens.access_token);
      onAuthenticated();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong");
    } finally {
      setWorking(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <h2>{mode === "login" ? "Log in" : "Create an account"}</h2>
      <label>
        Email
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      </label>
      <label>
        Password
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          minLength={8}
          required
        />
      </label>
      {error && <p className="error">{error}</p>}
      <button type="submit" disabled={working}>
        {working ? "…" : mode === "login" ? "Log in" : "Register & log in"}
      </button>
      <button type="button" className="link" onClick={() => setMode(mode === "login" ? "register" : "login")}>
        {mode === "login" ? "Need an account? Register" : "Already have an account? Log in"}
      </button>
    </form>
  );
}
