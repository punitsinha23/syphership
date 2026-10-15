// How often pages refresh while a deployment is still in progress
export const POLL_INTERVAL_MS = 3000

const IN_PROGRESS_STATUSES = new Set(["QUEUED", "BUILDING", "DEPLOYING"])

export function isInProgress(status) {
    return IN_PROGRESS_STATUSES.has(status)
}
