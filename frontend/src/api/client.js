export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"


let refreshPromise = null

async function refreshAccessToken() {
    const refreshToken = localStorage.getItem("refresh_token")

    if (!refreshToken) {
        throw new Error("No refresh token found")
    }

    const response = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            refresh_token: refreshToken
        })
    })

    const data = await response.json()

    if (!response.ok) {
        throw new Error(data.detail || "Token refresh failed")
    }

    localStorage.setItem("access_token", data.access_token)

    return data.access_token
}

export function saveSession({ access_token, refresh_token }) {
    localStorage.setItem("access_token", access_token)
    localStorage.setItem("refresh_token", refresh_token)
}

export function clearSession() {
    localStorage.removeItem("access_token")
    localStorage.removeItem("refresh_token")
}

function logout() {
    clearSession()
    window.location.href = "/login"
}

export function formatDetail(detail) {
    // FastAPI validation errors (422) return detail as a list of objects
    if (Array.isArray(detail)) {
        return detail.map((item) => item.msg).join(", ")
    }
    return detail
}

function requestError(message, status) {
    const error = new Error(message)
    error.status = status
    return error
}

function send(path, options, token) {
    return fetch(`${API_URL}${path}`, {
        ...options,
        headers: {
            ...options.headers,
            "Authorization": `Bearer ${token}`
        }
    })
}

export async function apiFetch(path, options = {}) {
    let response = await send(path, options, localStorage.getItem("access_token"))

    if (response.status === 401) {
        try {
            if (!refreshPromise) {
                refreshPromise = refreshAccessToken().finally(() => {
                    refreshPromise = null
                })
            }
            const newToken = await refreshPromise
            response = await send(path, options, newToken)
        } catch {
            logout()
            throw requestError("Session expired. Please log in again.", 401)
        }
    }

    if (!response.ok) {
        let errorMessage = `Request failed with status ${response.status}`
        try {
            const errorData = await response.json()
            errorMessage = formatDetail(errorData.detail) || errorMessage
        } catch {
            throw requestError(errorMessage, response.status)
        }
        throw requestError(errorMessage, response.status)
    }

    try {
        return await response.json()
    } catch {
        throw requestError(`Request failed with status ${response.status}`, response.status)
    }
}
