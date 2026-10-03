import { apiFetch } from "./client"

export async function getUser() {
    try {
        return await apiFetch("/auth/me")
    } catch {
        return null
    }
}
