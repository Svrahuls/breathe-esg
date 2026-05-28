import { useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Upload from "./pages/Upload";
import Review from "./pages/Review";
import { logout } from "./api/client";

export default function App() {
  const user = { username: "admin" }; // ← Dummy user, login skip

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