// Status is always shown as text + dot, never color alone
export function StatusBadge({ status }) {
    const label = status || "NO DEPLOYS"
    const modifier = status ? status.toLowerCase() : "none"

    return (
        <span className={`status status-${modifier}`}>
            <span className="status-dot" aria-hidden="true" />
            {label}
        </span>
    )
}
