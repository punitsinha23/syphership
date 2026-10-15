import { useEffect, useRef } from "react"
import { POLL_INTERVAL_MS } from "../utils/deployment"

// Calls refresh() every few seconds while `active` is true.
// Always calls the latest refresh, so it sees current props and state.
export function usePolling(active, refresh) {
    const refreshRef = useRef(refresh)

    useEffect(() => {
        refreshRef.current = refresh
    })

    useEffect(() => {
        if (!active) return

        const timer = setInterval(() => refreshRef.current(), POLL_INTERVAL_MS)
        return () => clearInterval(timer)
    }, [active])
}
