import { useEffect, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import "./GitHubCallback.css"

function GitHubCallback() {
    const [searchParams] = useSearchParams()
    const navigate = useNavigate()
    const [error, setError] = useState("")

    useEffect(() => {
        const accessToken = searchParams.get("access_token")
        const refreshToken = searchParams.get("refresh_token")

        if (accessToken && refreshToken) {
            localStorage.setItem("access_token", accessToken)
            localStorage.setItem("refresh_token", refreshToken)
            navigate("/dashboard")
        } else {
            setError("Authentication failed. Missing tokens.")
        }
    }, [searchParams, navigate])

    return (
        <div className="callback-page">
            <div className="callback-container">
                {error ? (
                    <>
                        <h1>Authentication Failed</h1>
                        <p className="callback-error">{error}</p>
                        <button
                            className="callback-button"
                            onClick={() => navigate("/")}
                        >
                            Back to Home
                        </button>
                    </>
                ) : (
                    <>
                        <div className="callback-spinner" />
                        <h1>Authenticating...</h1>
                        <p>Completing GitHub sign in</p>
                    </>
                )}
            </div>
        </div>
    )
}

export default GitHubCallback
