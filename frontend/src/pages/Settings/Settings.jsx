import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { connectGitHub } from "../../api/auth"
import { clearSession } from "../../api/client"
import { deleteAccount, getUser } from "../../api/user"
import { Navbar } from "../../components/Navbar/Navbar"
import "./Settings.css"

function Settings() {
    const [user, setUser] = useState(null)
    const [loading, setLoading] = useState(true)
    const [confirmation, setConfirmation] = useState("")
    const [deleting, setDeleting] = useState(false)
    const [connecting, setConnecting] = useState(false)
    const [error, setError] = useState(null)
    const navigate = useNavigate()

    useEffect(() => {
        getUser().then((data) => {
            setUser(data)
            setLoading(false)
        })
    }, [])

    async function handleConnectGitHub() {
        try {
            setConnecting(true)
            setError(null)
            await connectGitHub()
        } catch (error) {
            setError(error.message)
            setConnecting(false)
        }
    }

    async function handleDelete(event) {
        event.preventDefault()

        try {
            setDeleting(true)
            setError(null)
            await deleteAccount(confirmation)
            clearSession()
            navigate("/")
        } catch (error) {
            setError(error.message)
            setDeleting(false)
        }
    }

    return (
        <div className="app-page">
            <Navbar />

            <main className="app-container">
                <header className="page-header">
                    <div className="page-header-main">
                        <p className="eyebrow">Account</p>
                        <h1 className="page-title">Settings</h1>
                    </div>
                </header>

                {error && <div className="alert alert-error">{error}</div>}

                {loading && <div className="loading-state">Loading settings…</div>}

                {user && (
                    <>
                        <section className="section">
                            <div className="section-header">
                                <h2 className="section-title">Profile</h2>
                            </div>
                            <dl className="card settings-list">
                                <div>
                                    <dt>Username</dt>
                                    <dd>{user.username}</dd>
                                </div>
                                <div>
                                    <dt>Email</dt>
                                    <dd>{user.email}</dd>
                                </div>
                            </dl>
                        </section>

                        <section className="section">
                            <div className="section-header">
                                <h2 className="section-title">Connected accounts</h2>
                            </div>
                            <div className="card settings-list">
                                <div>
                                    <span>GitHub</span>
                                    {user.github_connected ? (
                                        <a
                                            className="settings-link"
                                            href="https://github.com/settings/applications"
                                            target="_blank"
                                            rel="noreferrer"
                                        >
                                            Connected · manage on GitHub
                                        </a>
                                    ) : (
                                        <button
                                            className="btn btn-secondary btn-sm"
                                            onClick={handleConnectGitHub}
                                            disabled={connecting}
                                        >
                                            {connecting ? "Redirecting…" : "Connect GitHub"}
                                        </button>
                                    )}
                                </div>
                                <div>
                                    <span>Google</span>
                                    <span className="settings-muted">
                                        {user.providers.includes("google") ? "Connected" : "Not connected"}
                                    </span>
                                </div>
                            </div>
                        </section>

                        <section className="section">
                            <div className="section-header">
                                <h2 className="section-title">Delete account</h2>
                            </div>
                            <form className="card settings-danger" onSubmit={handleDelete}>
                                <p>
                                    This permanently deletes your account, projects, deployments, build logs and
                                    environment variables, and takes your live apps offline. It can't be undone.
                                </p>
                                <p>
                                    To remove Syphership's GitHub access too, revoke it in your GitHub settings afterwards.
                                </p>
                                <label className="field">
                                    <span className="field-label">Type <strong>{user.username}</strong> to confirm</span>
                                    <input
                                        className="input"
                                        value={confirmation}
                                        onChange={(event) => setConfirmation(event.target.value)}
                                        autoComplete="off"
                                    />
                                </label>
                                <button
                                    className="btn btn-danger"
                                    type="submit"
                                    disabled={deleting || confirmation !== user.username}
                                >
                                    {deleting ? "Deleting…" : "Delete my account"}
                                </button>
                            </form>
                        </section>
                    </>
                )}
            </main>
        </div>
    )
}

export default Settings
