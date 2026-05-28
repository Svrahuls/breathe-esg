import { NavLink, useLocation } from "react-router-dom";

const NAV = [
  {
    to: "/",
    label: "Dashboard",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="w-5 h-5">
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
      </svg>
    ),
  },
  {
    to: "/upload",
    label: "Upload Data",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="w-5 h-5">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="17 8 12 3 7 8" />
        <line x1="12" y1="3" x2="12" y2="15" />
      </svg>
    ),
  },
  {
    to: "/review",
    label: "Review",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="w-5 h-5">
        <path d="M9 11l3 3L22 4" />
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
      </svg>
    ),
  },
];

export default function Sidebar() {
  return (
    <aside
      style={{ width: "var(--sidebar-width)" }}
      className="fixed inset-y-0 left-0 flex flex-col bg-slate-950 border-r border-slate-800/60 z-20"
    >
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-5 py-5 border-b border-slate-800/60">
        <div className="w-8 h-8 rounded-lg bg-emerald-500 flex items-center justify-center flex-shrink-0">
          <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" className="w-4.5 h-4.5">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" />
            <path d="M12 6v6l4 2" />
          </svg>
        </div>
        <div>
          <p className="text-sm font-600 text-white leading-tight">BreatheESG</p>
          <p className="text-[10px] text-slate-500 font-medium tracking-wide uppercase">
            Data Platform
          </p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        <p className="text-[10px] font-600 text-slate-600 uppercase tracking-widest px-2 mb-3">
          Navigation
        </p>
        {NAV.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                isActive
                  ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              }`
            }
          >
            {icon}
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-slate-800/60">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-full bg-emerald-700 flex items-center justify-center text-xs font-bold text-emerald-200">
            A
          </div>
          <div>
            <p className="text-xs font-medium text-slate-300">Analyst</p>
            <p className="text-[10px] text-slate-600">Default Org</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
