import axios from "axios";
const BASE_URL = "https://breathe-esg-vshf.onrender.com/api";

const TOKEN_KEY = "breathe_token";
export const getToken   = ()      => localStorage.getItem(TOKEN_KEY);
export const setToken   = (tok)   => localStorage.setItem(TOKEN_KEY, tok);
export const clearToken = ()      => localStorage.removeItem(TOKEN_KEY);

const client = axios.create({ baseURL: BASE_URL, timeout: 60000 });

// Har request pe token lagao
client.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Token ${token}`;
  return config;
});

// 401/403 pe logout, baaki errors normalize karo
client.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 || err.response?.status === 403) {
      clearToken();
      if (window.location.pathname !== "/login") window.location.href = "/login";
    }
    const msg = err.response?.data?.error || err.response?.data?.detail || err.message || "Unknown error";
    return Promise.reject(new Error(msg));
  }
);

// Auth
export const login = (username, password) =>
  client.post("/auth/login/", { username, password })  // client use karo, axios nahi
    .then((r) => { setToken(r.data.token); return r.data; });

export const logout = () =>
  client.post("/auth/logout/").finally(() => { clearToken(); window.location.href = "/login"; });

export const fetchMe = () => client.get("/auth/me/").then((r) => r.data);

// Dashboard
export const fetchStats = () => client.get("/dashboard/stats/").then((r) => r.data);

// Jobs
export const fetchJobs = () => client.get("/jobs/").then((r) => r.data);

// Records
export const fetchRecords = (params = {}) =>
  client.get("/records/", { params }).then((r) => r.data);

export const approveRecord = (id, note = "") =>
  client.patch(`/records/${id}/approve/`, { review_note: note }).then((r) => r.data);

export const rejectRecord = (id, note) =>
  client.patch(`/records/${id}/reject/`, { review_note: note }).then((r) => r.data);

export const bulkApprove = (ids) =>
  client.post("/records/bulk-approve/", { ids }).then((r) => r.data);

export const fetchAuditLog = (recordId) =>
  client.get(`/records/${recordId}/audit-log/`).then((r) => r.data);

// Ingestion
export const ingestFile = (sourceType, file, onProgress) => {
  const urlMap = { SAP: "/ingest/sap/", UTILITY: "/ingest/utility/", TRAVEL: "/ingest/travel/" };
  const url = urlMap[sourceType];
  if (!url) throw new Error(`Unknown source type: ${sourceType}`);
  const form = new FormData();
  form.append("file", file);
  return client.post(url, form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded * 100) / e.total));
    },
  }).then((r) => r.data);
};

export default client;