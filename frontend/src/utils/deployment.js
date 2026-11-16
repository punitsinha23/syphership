// How often pages refresh while a deployment is still in progress
export const POLL_INTERVAL_MS = 3000

const IN_PROGRESS_STATUSES = new Set(["QUEUED", "BUILDING", "DEPLOYING"])

export function isInProgress(status) {
    return IN_PROGRESS_STATUSES.has(status)
}

// Has a working address: running, or asleep and woken up by the next visit
const LIVE_STATUSES = new Set(["RUNNING", "SLEEPING", "WAKING"])

export function isLive(status) {
    return LIVE_STATUSES.has(status)
}
