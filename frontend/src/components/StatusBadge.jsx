export default function StatusBadge({ status }) {
  const config = {
    PENDING_REVIEW: { label: "Pending", cls: "badge-pending" },
    APPROVED: { label: "Approved", cls: "badge-approved" },
    REJECTED: { label: "Rejected", cls: "badge-rejected" },
    SUSPICIOUS: { label: "Suspicious", cls: "badge-suspicious" },
    DUPLICATE: { label: "Duplicate", cls: "badge-duplicate" },
    PENDING: { label: "Pending", cls: "badge-pending" },
    PROCESSING: { label: "Processing", cls: "bg-sky-500/15 text-sky-300 border border-sky-500/30" },
    DONE: { label: "Done", cls: "badge-approved" },
    FAILED: { label: "Failed", cls: "badge-rejected" },
  };

  const { label, cls } = config[status] || { label: status, cls: "badge-pending" };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium ${cls}`}>
      {label}
    </span>
  );
}
