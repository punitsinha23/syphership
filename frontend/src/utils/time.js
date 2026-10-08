// The API stores UTC but serializes naive datetimes (no "Z"), which the browser
// would otherwise read as local time.
export function parseApiDate(value) {
    if (!value) return null
    const hasZone = /[zZ]|[+-]\d\d:?\d\d$/.test(value)
    return new Date(hasZone ? value : `${value}Z`)
}

export function timeAgo(value) {
    const date = parseApiDate(value)
    if (!date) return ""

    const seconds = Math.round((Date.now() - date.getTime()) / 1000)
    if (seconds < 45) return "just now"

    const minutes = Math.round(seconds / 60)
    if (minutes < 60) return `${minutes}m ago`

    const hours = Math.round(minutes / 60)
    if (hours < 24) return `${hours}h ago`

    const days = Math.round(hours / 24)
    if (days < 30) return `${days}d ago`

    return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
}

export function formatDateTime(value) {
    const date = parseApiDate(value)
    if (!date) return ""

    return date.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
    })
}

export function shortSha(sha) {
    return sha ? sha.slice(0, 7) : ""
}
