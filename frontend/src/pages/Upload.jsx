import { useState, useRef } from "react";
import { ingestFile } from "../api/client";
import StatusBadge from "../components/StatusBadge";

const SOURCES = [
  {
    key: "SAP",
    label: "SAP Procurement",
    description: "Flat file export from SAP MM/FI module",
    accept: ".csv",
    scope: "Scope 1 — Fuel combustion",
    color: "emerald",
    icon: "⚙️",
  },
  {
    key: "UTILITY",
    label: "Utility Bills",
    description: "Electricity consumption CSV from utility portal",
    accept: ".csv",
    scope: "Scope 2 — Purchased electricity",
    color: "blue",
    icon: "⚡",
  },
  {
    key: "TRAVEL",
    label: "Travel (Concur)",
    description: "Concur TripLink or expense report CSV",
    accept: ".csv",
    scope: "Scope 3 — Business travel",
    color: "amber",
    icon: "✈️",
  },
];

function DropZone({ sourceKey, onUploadComplete }) {
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const fileRef = useRef();

  const handleFile = (f) => {
    setFile(f);
    setResult(null);
    setError(null);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setProgress(0);
    setError(null);
    try {
      const job = await ingestFile(sourceKey, file, setProgress);
      setResult(job);
      onUploadComplete?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const src = SOURCES.find((s) => s.key === sourceKey);
  const colorMap = {
    emerald: "border-emerald-500/40 bg-emerald-500/5",
    blue: "border-blue-500/40 bg-blue-500/5",
    amber: "border-amber-500/40 bg-amber-500/5",
  };

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        className={`border-2 border-dashed rounded-xl p-10 text-center transition-all duration-200 cursor-pointer
          ${dragging ? colorMap[src.color] : "border-slate-700 hover:border-slate-600"}
        `}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileRef.current?.click()}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => handleFile(e.target.files[0])}
        />
        <div className="text-4xl mb-3">{src.icon}</div>
        {file ? (
          <div>
            <p className="text-slate-200 font-medium">{file.name}</p>
            <p className="text-slate-500 text-xs mt-1">{(file.size / 1024).toFixed(1)} KB</p>
          </div>
        ) : (
          <div>
            <p className="text-slate-300 font-medium">Drop CSV file here</p>
            <p className="text-slate-600 text-sm mt-1">or click to browse</p>
          </div>
        )}
      </div>

      {/* Upload button + progress */}
      {file && !result && (
        <div className="space-y-3">
          {uploading && (
            <div>
              <div className="flex justify-between text-xs text-slate-500 mb-1">
                <span>Uploading…</span>
                <span>{progress}%</span>
              </div>
              <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-500 transition-all duration-300 rounded-full"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="btn-primary w-full"
          >
            {uploading ? "Processing…" : "Upload & Ingest"}
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-sm text-red-300">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-slate-200">Ingestion Complete</span>
            <StatusBadge status={result.status} />
          </div>
          <div className="grid grid-cols-4 gap-3 text-center">
            {[
              { label: "Total", val: result.total_rows, cls: "text-slate-300" },
              { label: "Success", val: result.success_rows, cls: "text-emerald-400" },
              { label: "Suspicious", val: result.suspicious_rows, cls: "text-amber-400" },
              { label: "Duplicates", val: result.duplicate_rows, cls: "text-purple-400" },
            ].map(({ label, val, cls }) => (
              <div key={label} className="bg-slate-900 rounded-lg py-3">
                <p className={`text-2xl font-bold ${cls}`}>{val}</p>
                <p className="text-xs text-slate-500 mt-0.5">{label}</p>
              </div>
            ))}
          </div>
          {result.error_message && (
            <p className="text-xs text-red-400 font-mono bg-red-500/5 rounded p-2">
              {result.error_message}
            </p>
          )}
          <button
            onClick={() => { setFile(null); setResult(null); }}
            className="btn-ghost w-full text-sm"
          >
            Upload Another File
          </button>
        </div>
      )}
    </div>
  );
}

export default function Upload() {
  const [activeTab, setActiveTab] = useState("SAP");
  const [refreshKey, setRefreshKey] = useState(0);

  const tabColor = { SAP: "emerald", UTILITY: "blue", TRAVEL: "amber" };
  const activeColorMap = {
    emerald: "border-emerald-500 text-emerald-400 bg-emerald-500/10",
    blue: "border-blue-500 text-blue-400 bg-blue-500/10",
    amber: "border-amber-500 text-amber-400 bg-amber-500/10",
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Upload Emissions Data</h1>
        <p className="text-sm text-slate-500 mt-1">
          Ingest CSV files from SAP, utility providers, or Concur travel
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-900 border border-slate-800 rounded-xl p-1">
        {SOURCES.map((src) => {
          const isActive = activeTab === src.key;
          const c = tabColor[src.key];
          return (
            <button
              key={src.key}
              onClick={() => setActiveTab(src.key)}
              className={`flex-1 py-2.5 px-3 rounded-lg text-sm font-medium transition-all duration-150 border
                ${isActive
                  ? activeColorMap[c]
                  : "border-transparent text-slate-500 hover:text-slate-300"
                }`}
            >
              <span className="mr-1.5">{src.icon}</span>
              {src.label}
            </button>
          );
        })}
      </div>

      {/* Active source info */}
      {SOURCES.filter((s) => s.key === activeTab).map((src) => (
        <div key={src.key} className="card p-5">
          <div className="flex items-start justify-between mb-5">
            <div>
              <h2 className="font-semibold text-slate-200">{src.label}</h2>
              <p className="text-sm text-slate-500 mt-0.5">{src.description}</p>
            </div>
            <span className="text-xs bg-slate-800 border border-slate-700 px-2.5 py-1 rounded-lg text-slate-400 font-medium whitespace-nowrap">
              {src.scope}
            </span>
          </div>
         <DropZone
  key={src.key}
  sourceKey={src.key}
  onUploadComplete={() => setRefreshKey((k) => k + 1)}
/>
        </div>
      ))}

      {/* Tips */}
      <div className="card p-4 bg-slate-900/50">
        <p className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wide">
          Expected Columns
        </p>
        <div className="space-y-1">
          {activeTab === "SAP" && (
            <p className="text-xs font-mono text-slate-500">
              MANDT, BUKRS, BELNR, BLDAT, MATNR, MENGE, MEINS, WERKS, LIFNR, DMBTR, WAERS
            </p>
          )}
          {activeTab === "UTILITY" && (
            <p className="text-xs font-mono text-slate-500">
              account_number, billing_period_start, billing_period_end, meter_id,
              consumption_kwh, tariff_rate, total_amount_gbp, carbon_intensity_gco2_per_kwh
            </p>
          )}
          {activeTab === "TRAVEL" && (
            <p className="text-xs font-mono text-slate-500">
              employee_id, trip_date, travel_type, origin, destination, distance_km, nights,
              transport_class, amount_usd, currency
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
