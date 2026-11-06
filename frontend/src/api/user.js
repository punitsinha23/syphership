import { apiFetch } from "./client"

export async function getUser() {
    try {
        return await apiFetch("/auth/me")
    } catch {
        return null
    }
}

export function deleteAccount(confirmUsername) {
    return apiFetch("/auth/me", {
        method: "DELETE",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ confirm_username: confirmUsername })
    })
}
