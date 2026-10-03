const API_URL = "http://localhost:8000"


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

function logout() {
    localStorage.removeItem("access_token")
    localStorage.removeItem("refresh_token")
    window.location.href = "/login"
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
            throw new Error("Session expired. Please log in again.")
        }
    }

    const data = await response.json()

    if (!response.ok) {
        throw new Error(data.detail || "Request failed")
    }

    return data
}
