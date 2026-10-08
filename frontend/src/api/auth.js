import { API_URL, apiFetch, formatDetail } from "./client"

// Sign-in starts with a full-page navigation to the API, which redirects to the provider
export function providerLoginUrl(provider) {
    return `${API_URL}/${provider}/login`
}

// Trade the one-time code from /auth/callback for session tokens
export async function exchangeLoginCode(code) {
    const response = await fetch(`${API_URL}/auth/exchange`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ code })
    })

    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
        throw new Error(formatDetail(data.detail) || "Sign-in failed. Please try again.")
    }

    return data
}

const CONNECT_RETURN_KEY = "connect_return_path"

// Where to go after a "Connect GitHub" round trip; cleared once read
export function takeConnectReturnPath() {
    const path = sessionStorage.getItem(CONNECT_RETURN_KEY)
    sessionStorage.removeItem(CONNECT_RETURN_KEY)
    return path || "/dashboard"
}

// Link GitHub to the signed-in account. credentials: "include" lets the API
// set the state cookie that its callback checks.
export async function connectGitHub() {
    sessionStorage.setItem(CONNECT_RETURN_KEY, window.location.pathname)

    const { url } = await apiFetch("/github/connect", {
        method: "POST",
        credentials: "include"
    })

    window.location.href = url
}
