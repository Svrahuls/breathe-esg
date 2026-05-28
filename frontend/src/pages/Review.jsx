import React, { useEffect, useState, useCallback } from "react";
import { fetchRecords, approveRecord, rejectRecord, bulkApprove, fetchAuditLog } from "../api/client";
import StatusBadge from "../components/StatusBadge";

// ─── Reject modal ─────────────────────────────────────────────────────────────

function RejectModal({ record, onClose, onConfirm }) {
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!note.trim()) return;
    setSubmitting(true);
    try {
      await onConfirm(record.id, note);
      onClose();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="card w-full max-w-md p-6 space-y-4 shadow-2xl">
        <h3 className="font-semibold text-slate-200">Reject Record</h3>
        <p className="text-sm text-slate-500">
          Please provide a reason for rejecting this record.
        </p>
        <div>
          <p className="text-xs text-slate-400 mb-2">{record?.description?.slice(0, 100)}…</p>
          <textarea
            className="input w-full resize-none h-24"
            placeholder="Enter rejection reason…"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            autoFocus
          />
        </div>
        <div className="flex gap-3 justify-end">
          <button onClick={onClose} className="btn-ghost text-sm">Cancel</button>
          <button
            onClick={handleSubmit}
            disabled={!note.trim() || submitting}
            className="bg-red-600 hover:bg-red-500 text-white font-medium px-4 py-2 rounded-lg
                       transition-colors disabled:opacity-40 disabled:cursor-not-allowed text-sm"
          >
            {submitting ? "Rejecting…" : "Confirm Reject"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Audit log drawer (BUG-06 FIX) ───────────────────────────────────────────

function AuditLogDrawer({ record, onClose }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAuditLog(record.id)
      .then(setLogs)
      .catch(() => setLogs([]))
      .finally(() => setLoading(false));
  }, [record.id]);

  const ACTION_STYLES = {
    APPROVED: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
    BULK_APPROVED: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
    REJECTED: "text-red-400 bg-red-500/10 border-red-500/30",
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-end sm:items-center justify-center p-4">
      <div className="card w-full max-w-lg max-h-[80vh] flex flex-col shadow-2xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
          <div>
            <h3 className="font-semibold text-slate-200">Audit Log</h3>
            <p className="text-xs text-slate-500 mt-0.5 font-mono truncate">{record.id}</p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 text-lg">✕</button>
        </div>

        <div className="overflow-y-auto flex-1 px-5 py-4 space-y-3">
          {loading ? (
            <p className="text-slate-600 text-sm animate-pulse">Loading…</p>
          ) : logs.length === 0 ? (
            <p className="text-slate-600 text-sm">No actions recorded yet.</p>
          ) : (
            logs.map((log) => (
              <div key={log.id} className="border border-slate-800 rounded-lg p-3 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded border ${
                      ACTION_STYLES[log.action] || "text-slate-400 bg-slate-800 border-slate-700"
                    }`}
                  >
                    {log.action}
                  </span>
                  <span className="text-xs text-slate-500 font-mono">
                    {new Date(log.changed_at).toLocaleString()}
                  </span>
                </div>
                {log.changed_by_username && (
                  <p className="text-xs text-slate-400">by {log.changed_by_username}</p>
                )}
                {log.after_data?.review_note && (
                  <p className="text-xs text-amber-300/80 bg-amber-500/5 border border-amber-500/20 rounded px-2 py-1">
                    "{log.after_data.review_note}"
                  </p>
                )}
                <div className="flex gap-2 text-xs text-slate-600 font-mono">
                  <span>{log.before_data?.status}</span>
                  <span>→</span>
                  <span>{log.after_data?.status}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Parser flags display ─────────────────────────────────────────────────────

function ParserFlags({ flags }) {
  if (!flags || flags.length === 0) return null;
  const FLAG_COLORS = {
    LONG_BILLING_PERIOD: "text-orange-300 bg-orange-500/10 border-orange-500/30",
    DEFAULT_CARBON_INTENSITY: "text-yellow-300 bg-yellow-500/10 border-yellow-500/30",
    ZERO_OR_NEGATIVE: "text-red-400 bg-red-500/10 border-red-500/30",
    NEGATIVE_DISTANCE: "text-red-400 bg-red-500/10 border-red-500/30",
    UNKNOWN_UNIT: "text-purple-400 bg-purple-500/10 border-purple-500/30",
    MISSING_FLIGHT_DISTANCE: "text-orange-300 bg-orange-500/10 border-orange-500/30",
  };
  return (
    <div className="flex flex-wrap gap-1 mt-1.5">
      {flags.map((flag) => (
        <span
          key={flag}
          className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
            FLAG_COLORS[flag] || "text-slate-400 bg-slate-800 border-slate-700"
          }`}
        >
          {flag}
        </span>
      ))}
    </div>
  );
}

// ─── Raw data panel ───────────────────────────────────────────────────────────

function RawDataPanel({ rawData }) {
  return (
    <div className="bg-slate-950 rounded-lg p-4 overflow-auto max-h-48 border border-slate-800">
      <pre className="text-xs font-mono text-slate-400 whitespace-pre-wrap">
        {JSON.stringify(rawData, null, 2)}
      </pre>
    </div>
  );
}

// ─── Constants ────────────────────────────────────────────────────────────────

const SCOPE_LABELS = { 1: "Scope 1", 2: "Scope 2", 3: "Scope 3" };
const CATEGORY_ICONS = {
  fuel: "🔥",
  electricity: "⚡",
  flight: "✈️",
  hotel: "🏨",
  ground: "🚗",
};

// ─── Main component ───────────────────────────────────────────────────────────

export default function Review() {
  const [records, setRecords] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    status: "",
    scope: "",
    source_type: "",
    date_from: "",
    date_to: "",
  });
  const [expanded, setExpanded] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [rejectTarget, setRejectTarget] = useState(null);
  const [auditTarget, setAuditTarget] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        page,
        page_size: 20,
        ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)),
      };
      const data = await fetchRecords(params);
      setRecords(data.results);
      setTotal(data.count);
    } finally {
      setLoading(false);
    }
  }, [page, filters]);

  useEffect(() => { load(); }, [load]);

  const handleApprove = async (id) => {
    setActionLoading(id);
    try {
      const updated = await approveRecord(id);
      setRecords((rs) => rs.map((r) => (r.id === id ? updated : r)));
    } finally {
      setActionLoading(null);
    }
  };

  const handleRejectConfirm = async (id, note) => {
    setActionLoading(id);
    try {
      const updated = await rejectRecord(id, note);
      setRecords((rs) => rs.map((r) => (r.id === id ? updated : r)));
    } finally {
      setActionLoading(null);
    }
  };

  const handleBulkApprove = async () => {
    if (!selected.size) return;
    setLoading(true);
    try {
      await bulkApprove([...selected]);
      setSelected(new Set());
      load();
    } finally {
      setLoading(false);
    }
  };

  const toggleSelect = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    const reviewable = records.filter((r) => !r.is_locked && r.status === "PENDING_REVIEW");
    if (selected.size === reviewable.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(reviewable.map((r) => r.id)));
    }
  };

  const totalPages = Math.ceil(total / 20);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Review Records</h1>
          <p className="text-sm text-slate-500 mt-1">{total} total records</p>
        </div>
        {selected.size > 0 && (
          <button onClick={handleBulkApprove} className="btn-primary">
            ✓ Bulk Approve ({selected.size})
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="card p-4 flex flex-wrap gap-3">
        <select
          className="input"
          value={filters.status}
          onChange={(e) => { setFilters((f) => ({ ...f, status: e.target.value })); setPage(1); }}
        >
          <option value="">All Statuses</option>
          <option value="PENDING_REVIEW">Pending Review</option>
          <option value="APPROVED">Approved</option>
          <option value="REJECTED">Rejected</option>
          <option value="SUSPICIOUS">Suspicious</option>
        </select>

        <select
          className="input"
          value={filters.scope}
          onChange={(e) => { setFilters((f) => ({ ...f, scope: e.target.value })); setPage(1); }}
        >
          <option value="">All Scopes</option>
          <option value="1">Scope 1</option>
          <option value="2">Scope 2</option>
          <option value="3">Scope 3</option>
        </select>

        <select
          className="input"
          value={filters.source_type}
          onChange={(e) => { setFilters((f) => ({ ...f, source_type: e.target.value })); setPage(1); }}
        >
          <option value="">All Sources</option>
          <option value="SAP">SAP</option>
          <option value="UTILITY">Utility</option>
          <option value="TRAVEL">Travel</option>
        </select>

       <div className="flex items-center gap-1.5">
  <span className="text-xs text-slate-500 whitespace-nowrap">From:</span>
  <input
    type="date"
    className="input"
    value={filters.date_from}
    onChange={(e) => { setFilters((f) => ({ ...f, date_from: e.target.value })); setPage(1); }}
  />
</div>
<div className="flex items-center gap-1.5">
  <span className="text-xs text-slate-500 whitespace-nowrap">To:</span>
  <input
    type="date"
    className="input"
    value={filters.date_to}
    onChange={(e) => { setFilters((f) => ({ ...f, date_to: e.target.value })); setPage(1); }}
  />
</div>
       
        <button
  onClick={() => {
    setFilters({ status: "", scope: "", source_type: "", date_from: "", date_to: "" });
    setPage(1);
    // date inputs force reset
    document.querySelectorAll('input[type="date"]').forEach(el => el.value = "");
  }}
  className="btn-ghost text-sm"
>
  Clear
</button>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="py-16 text-center text-slate-600 text-sm animate-pulse">Loading records…</div>
        ) : records.length === 0 ? (
          <div className="py-16 text-center text-slate-600 text-sm">No records found</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800">
                  <th className="px-4 py-3 text-left w-8">
                    <input
                      type="checkbox"
                      className="rounded border-slate-600 bg-slate-800"
                      onChange={selectAll}
                      checked={
                        selected.size > 0 &&
                        selected.size ===
                          records.filter((r) => !r.is_locked && r.status === "PENDING_REVIEW").length
                      }
                    />
                  </th>
                  {["Date", "Source", "Category", "Quantity", "Scope", "Status", "Actions"].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {records.map((record) => {
                  const isSuspicious = record.status === "SUSPICIOUS";
                  const isExpanded = expanded === record.id;

                  // BUG FIX: bare <> fragments cannot carry a key prop.
                  // Must use <React.Fragment key=...> so React can track rows correctly.
                  return (
                    <React.Fragment key={record.id}>
                      <tr
                        className={`border-b border-slate-800/50 transition-colors cursor-pointer
                          ${isSuspicious ? "bg-amber-500/5 hover:bg-amber-500/8" : "hover:bg-slate-800/30"}
                          ${isExpanded ? "bg-slate-800/40" : ""}
                        `}
                        onClick={() => setExpanded(isExpanded ? null : record.id)}
                      >
                        <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                          {!record.is_locked && record.status === "PENDING_REVIEW" && (
                            <input
                              type="checkbox"
                              className="rounded border-slate-600 bg-slate-800"
                              checked={selected.has(record.id)}
                              onChange={() => toggleSelect(record.id)}
                            />
                          )}
                        </td>
                        <td className="px-4 py-3 text-slate-400 text-xs font-mono whitespace-nowrap">
                          {record.activity_date || "—"}
                        </td>
                        <td className="px-4 py-3 text-xs font-medium text-slate-300">
                          {record.source_type || "—"}
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-base mr-1.5">{CATEGORY_ICONS[record.category] || "📊"}</span>
                          <span className="text-slate-300 text-xs capitalize">{record.category}</span>
                        </td>
                        <td className="px-4 py-3 font-mono text-xs text-slate-300">
                          {record.normalized_quantity
                            ? parseFloat(record.normalized_quantity).toFixed(2)
                            : "—"}{" "}
                          <span className="text-slate-600">{record.normalized_unit}</span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-xs text-slate-500 bg-slate-800 px-2 py-0.5 rounded">
                            {SCOPE_LABELS[record.scope] || "—"}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1.5">
                            <StatusBadge status={record.status} />
                            {record.is_locked && <span title="Locked" className="text-xs">🔒</span>}
                          </div>
                        </td>
                        <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                          <div className="flex gap-1.5">
                            {!record.is_locked &&
                              (record.status === "PENDING_REVIEW" || record.status === "SUSPICIOUS") && (
                                <>
                                  <button
                                    onClick={() => handleApprove(record.id)}
                                    disabled={actionLoading === record.id}
                                    className="text-xs bg-emerald-600/20 hover:bg-emerald-600/40 text-emerald-400
                                               border border-emerald-600/30 px-2.5 py-1 rounded-md transition-colors"
                                    title="Approve"
                                  >
                                    ✓
                                  </button>
                                  <button
                                    onClick={() => setRejectTarget(record)}
                                    disabled={actionLoading === record.id}
                                    className="text-xs bg-red-600/20 hover:bg-red-600/40 text-red-400
                                               border border-red-600/30 px-2.5 py-1 rounded-md transition-colors"
                                    title="Reject"
                                  >
                                    ✕
                                  </button>
                                </>
                              )}
                            {/* BUG-06 FIX: audit log button — visible on all locked records */}
                            {record.is_locked && (
                              <button
                                onClick={() => setAuditTarget(record)}
                                className="text-xs bg-slate-700/50 hover:bg-slate-700 text-slate-400
                                           border border-slate-700 px-2.5 py-1 rounded-md transition-colors"
                                title="View audit log"
                              >
                                📋
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>

                      {/* Expanded row */}
                      {isExpanded && (
                        <tr className="bg-slate-900/80">
                          <td colSpan={8} className="px-6 py-4">
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                              <div className="space-y-2">
                                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
                                  Description
                                </p>
                                <p className="text-xs text-slate-300">{record.description}</p>
                                <p className="text-xs text-slate-500">
                                  📍 {record.location || "No location"}
                                </p>
                                {/* Parser flags — now visible to analysts */}
                                <ParserFlags flags={record.parser_flags} />
                                {record.review_note && (
                                  <p className="text-xs text-amber-300 bg-amber-500/10 border border-amber-500/20 rounded px-3 py-2">
                                    Note: {record.review_note}
                                  </p>
                                )}
                              </div>
                              <div className="space-y-2">
                                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
                                  Raw Source Data
                                </p>
                                <RawDataPanel rawData={record.raw_data} />
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-500">Page {page} of {totalPages}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="btn-ghost text-sm disabled:opacity-30"
            >
              ← Prev
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="btn-ghost text-sm disabled:opacity-30"
            >
              Next →
            </button>
          </div>
        </div>
      )}

      {/* Modals */}
      {rejectTarget && (
        <RejectModal
          record={rejectTarget}
          onClose={() => setRejectTarget(null)}
          onConfirm={handleRejectConfirm}
        />
      )}
      {auditTarget && (
        <AuditLogDrawer
          record={auditTarget}
          onClose={() => setAuditTarget(null)}
        />
      )}
    </div>
  );
}
