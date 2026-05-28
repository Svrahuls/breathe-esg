import { useEffect, useState } from "react";
import { fetchStats, fetchJobs } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

const SCOPE_COLORS = ["#22c55e", "#3b82f6", "#f59e0b"];
const SOURCE_COLORS = { SAP: "#22c55e", UTILITY: "#3b82f6", TRAVEL: "#f59e0b" };

function StatCard({ label, value, sub, color = "emerald" }) {
  const colorMap = {
    emerald: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    blue: "text-blue-400 bg-blue-500/10 border-blue-500/20",
    amber: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    red: "text-red-400 bg-red-500/10 border-red-500/20",
    slate: "text-slate-300 bg-slate-800/80 border-slate-700/50",
  };
  return (
    <div className={`card p-5 border ${colorMap[color]}`}>
      <p className="text-xs font-medium uppercase tracking-wider text-slate-500 mb-2">{label}</p>
      <p className={`text-3xl font-bold ${colorMap[color].split(" ")[0]}`}>{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  );
}

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200">
      <p className="font-medium">{payload[0].name}</p>
      <p>{payload[0].value} records</p>
    </div>
  );
};

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchStats(), fetchJobs()])
      .then(([s, j]) => {
        setStats(s);
        setJobs(j.slice(0, 8));
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-500 text-sm animate-pulse">Loading dashboard…</div>
      </div>
    );
  }

  const scopeData = [
    { name: "Scope 1", value: stats?.scope_1 || 0 },
    { name: "Scope 2", value: stats?.scope_2 || 0 },
    { name: "Scope 3", value: stats?.scope_3 || 0 },
  ].filter((d) => d.value > 0);

  const sourceData = (stats?.by_source || []).map((s) => ({
    name: s.source_type || "Unknown",
    Records: s.count,
    kgCO2e: parseFloat(s.total_kgco2e || 0).toFixed(1),
  }));

  const totalKg = parseFloat(stats?.total_kgco2e || 0);
  const totalTons = (totalKg / 1000).toFixed(2);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Emissions Dashboard</h1>
        <p className="text-sm text-slate-500 mt-1">
          Real-time overview of ingested and reviewed records
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard label="Total Records" value={stats?.total_records ?? "—"} color="slate" />
        <StatCard label="Pending Review" value={stats?.pending_review ?? "—"} color="blue" />
        <StatCard label="Approved" value={stats?.approved ?? "—"} color="emerald" />
        <StatCard label="Suspicious" value={stats?.suspicious ?? "—"} color="amber" />
        <StatCard
          label="Total CO₂e"
          value={`${totalTons} t`}
          sub="tonnes CO₂ equivalent"
          color="red"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Scope donut */}
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Records by Scope</h2>
          {scopeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={scopeData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {scopeData.map((entry, i) => (
                    <Cell key={entry.name} fill={SCOPE_COLORS[i % SCOPE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  formatter={(v) => <span className="text-xs text-slate-400">{v}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-slate-600 text-sm text-center py-12">No data yet</p>
          )}
        </div>

        {/* Source bar */}
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Records by Source</h2>
          {sourceData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={sourceData} barCategoryGap="30%">
                <XAxis
                  dataKey="name"
                  tick={{ fill: "#64748b", fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "#64748b", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  cursor={{ fill: "rgba(255,255,255,0.03)" }}
                  contentStyle={{
                    background: "#1e293b",
                    border: "1px solid #334155",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  labelStyle={{ color: "#94a3b8" }}
                />
                <Bar dataKey="Records" radius={[4, 4, 0, 0]}>
                  {sourceData.map((entry) => (
                    <Cell
                      key={entry.name}
                      fill={SOURCE_COLORS[entry.name] || "#6366f1"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-slate-600 text-sm text-center py-12">No data yet</p>
          )}
        </div>
      </div>

      {/* Recent jobs */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-800">
          <h2 className="text-sm font-semibold text-slate-300">Recent Ingestion Jobs</h2>
        </div>
        {jobs.length === 0 ? (
          <p className="text-slate-600 text-sm text-center py-10">No ingestion jobs yet</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800">
                  {["File", "Source", "Status", "Total", "Success", "Suspicious", "Dupes", "When"].map(
                    (h) => (
                      <th
                        key={h}
                        className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider"
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {jobs.map((job, i) => (
                  <tr
                    key={job.id}
                    className={`border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors ${
                      i % 2 === 0 ? "" : "bg-slate-900/30"
                    }`}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-slate-300 max-w-[160px] truncate">
                      {job.file_name}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-slate-400 font-medium">{job.source_type}</span>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={job.status} />
                    </td>
                    <td className="px-4 py-3 text-slate-300">{job.total_rows}</td>
                    <td className="px-4 py-3 text-emerald-400">{job.success_rows}</td>
                    <td className="px-4 py-3 text-amber-400">{job.suspicious_rows}</td>
                    <td className="px-4 py-3 text-purple-400">{job.duplicate_rows}</td>
                    <td className="px-4 py-3 text-slate-500 text-xs">
                      {new Date(job.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
