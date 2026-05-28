import { useState } from "react";
import { login } from "../api/client";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await login(username.trim(), password);
      onLogin(data.user);
    } catch (err) {
      // ✅ Sahi
setError(error.response?.data?.detail || error.response?.data?.message || error.message || "Login failed")
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#080f1e] flex items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-8">
        <div className="text-center space-y-2">
          <span className="text-4xl">🌿</span>
          <h1 className="text-2xl font-bold text-white">Breathe ESG</h1>
          <p className="text-sm text-slate-500">Sign in to your account</p>
        </div>
        <form onSubmit={handleSubmit} className="card p-6 space-y-5 border border-slate-800">
          {error && (
            <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3">
              {error}
            </div>
          )}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-400 uppercase tracking-wide">Username</label>
            <input type="text" className="input w-full" placeholder="admin"
              value={username} onChange={(e) => setUsername(e.target.value)} autoFocus required />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-400 uppercase tracking-wide">Password</label>
            <input type="password" className="input w-full" placeholder="••••••••"
              value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <button type="submit" disabled={loading || !username || !password}
            className="w-full btn-primary py-2.5 disabled:opacity-40 disabled:cursor-not-allowed">
            {loading ? "Signing in…" : "Sign In"}
          </button>
        </form>
        <p className="text-center text-xs text-slate-600">
          No account? Run <code className="bg-slate-800 px-1.5 py-0.5 rounded text-slate-400">python manage.py createsuperuser</code>
        </p>
      </div>
    </div>
  );
}