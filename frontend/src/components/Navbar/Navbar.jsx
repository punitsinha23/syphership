import { NavLink, Link, useNavigate } from "react-router-dom"
import { getUser } from "../../api/user"
import { clearSession } from "../../api/client"
import { useEffect, useState } from "react"
import "./Navbar.css"

const LINKS = [
    {
        to: "/dashboard",
        label: "Overview",
        icon: <path d="M3 3h7v7H3zM14 3h7v4h-7zM14 11h7v10h-7zM3 14h7v7H3z" />,
    },
    {
        to: "/projects",
        label: "Projects",
        icon: <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />,
    },
]

export function Navbar() {
    const navigate = useNavigate()
    const [user, setUser] = useState(null)

    useEffect(() => {
        getUser().then(setUser)
    }, [])

    function handleLogout() {
        clearSession()
        navigate("/")
    }

    return (
        <nav className="navbar" aria-label="Main">
            <Link className="navbar-logo" to="/dashboard">
                <span>SYPHER</span>
                <span className="navbar-logo-accent">//</span>
                <span>SHIP</span>
            </Link>

            <div className="navbar-links">
                {LINKS.map((link) => (
                    <NavLink
                        key={link.to}
                        to={link.to}
                        className={({ isActive }) => `navbar-link ${isActive ? "active" : ""}`}
                    >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" aria-hidden="true">
                            {link.icon}
                        </svg>
                        {link.label}
                    </NavLink>
                ))}
            </div>

            <div className="navbar-user">
                {user && (
                    <div className="navbar-profile">
                        {user.avatar_url ? (
                            <img className="navbar-avatar" src={user.avatar_url} alt="" />
                        ) : (
                            <span className="navbar-avatar navbar-avatar-fallback" aria-hidden="true">
                                {user.username.charAt(0).toUpperCase()}
                            </span>
                        )}
                        <div className="navbar-profile-text">
                            <span className="navbar-username">{user.username}</span>
                            <span className="navbar-email">{user.email}</span>
                        </div>
                    </div>
                )}
                <button className="navbar-logout" onClick={handleLogout} title="Log out" aria-label="Log out">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
                    </svg>
                </button>
            </div>
        </nav>
    )
}
