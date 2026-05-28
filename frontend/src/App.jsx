import { useState, useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Upload from "./pages/Upload";
import Review from "./pages/Review";
import Login from "./pages/login";
import { getToken, fetchMe, logout } from "./api/client";

export default function App() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    if (!getToken()) { setUser(false); return; }
    fetchMe().then(setUser).catch(() => setUser(false));
  }, []);

  if (user === null) return (
    <div className="min-h-screen bg-[#080f1e] flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
    </div>
  );

  if (user === false) return <Login onLogin={setUser} />;

  return (
    <div className="flex min-h-screen">
      <Sidebar user={user} onLogout={logout} />
      <main style={{ marginLeft: "var(--sidebar-width)" }} className="flex-1 min-h-screen p-6 lg:p-8 bg-[#080f1e]">
        <Routes>
          <Route path="/"       element={<Dashboard />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/review" element={<Review />} />
          <Route path="*"       element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}