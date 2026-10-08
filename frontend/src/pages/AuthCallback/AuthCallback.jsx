import { useEffect, useRef, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { exchangeLoginCode, takeConnectReturnPath } from "../../api/auth"
import { saveSession } from "../../api/client"
import "./AuthCallback.css"

// The API redirects here after GitHub/Google with exactly one of:
//   ?code=...         sign-in succeeded, exchange the one-time code for tokens
//   ?connected=github  a provider was linked to the signed-in account
//   ?error=...        something went wrong
function AuthCallback() {
    const [searchParams] = useSearchParams()
    const navigate = useNavigate()
    const [exchangeError, setExchangeError] = useState("")
    // StrictMode runs effects twice in dev; the code is single-use
    const handled = useRef(false)

    const code = searchParams.get("code")
    const connected = searchParams.get("connected")
    const urlError = searchParams.get("error")
    const error = urlError || exchangeError ||
        (!code && !connected ? "Authentication failed. Missing sign-in code." : "")

    useEffect(() => {
        if (handled.current) return
        handled.current = true

        if (connected) {
            navigate(takeConnectReturnPath(), { replace: true })
            return
        }

        if (urlError) {
            // Don't strand a signed-in user on a failed "Connect GitHub"
            takeConnectReturnPath()
            return
        }

        if (!code) return

        exchangeLoginCode(code)
            .then((tokens) => {
                saveSession(tokens)
                navigate("/dashboard", { replace: true })
            })
            .catch((err) => setExchangeError(err.message))
    }, [code, connected, urlError, navigate])

    const signedIn = Boolean(localStorage.getItem("access_token"))

    return (
        <div className="callback-page">
            <div className="callback-container">
                {error ? (
                    <>
                        <h1>Authentication Failed</h1>
                        <p className="callback-error">{error}</p>
                        <button
                            className="callback-button"
                            onClick={() => navigate(signedIn ? "/dashboard" : "/login", { replace: true })}
                        >
                            {signedIn ? "Back to dashboard" : "Back to sign in"}
                        </button>
                    </>
                ) : (
                    <>
                        <div className="callback-spinner" />
                        <h1>Authenticating...</h1>
                        <p>Completing sign in</p>
                    </>
                )}
            </div>
        </div>
    )
}

export default AuthCallback
