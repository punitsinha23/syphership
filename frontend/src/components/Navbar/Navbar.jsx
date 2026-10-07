import { useNavigate, useLocation } from "react-router-dom"
import { getUser } from "../../api/user"
import { useEffect, useState } from "react"
import "./Navbar.css"

export function Navbar() {
    const navigate = useNavigate()
    const location = useLocation()
    const [username, setUsername] = useState("")

    useEffect(() => {
        async function loadUser() {
            const user = await getUser()
            if (user) setUsername(user.username)
        }
        loadUser()
    }, [])

    function isActive(path) {
        return location.pathname.startsWith(path)
    }

    function handleLogout() {
        localStorage.removeItem("access_token")
        localStorage.removeItem("refresh_token")
        navigate("/")
    }

    return (
        <nav className="navbar">
            <div className="navbar-logo" onClick={() => navigate("/dashboard")}>
                <span>SYPHER</span>
                <span className="navbar-logo-accent">//</span>
                <span>SHIP</span>
            </div>

            <div className="navbar-links">
                <button
                    className={`navbar-link ${isActive("/dashboard") ? "active" : ""}`}
                    onClick={() => navigate("/dashboard")}
                >
                    Dashboard
                </button>
                <button
                    className={`navbar-link ${isActive("/projects") ? "active" : ""}`}
                    onClick={() => navigate("/projects")}
                >
                    Projects
                </button>
            </div>

            <div className="navbar-user">
                {username && <span className="navbar-username">{username}</span>}
                <button className="navbar-logout" onClick={handleLogout}>
                    Logout
                </button>
            </div>
        </nav>
    )
}
