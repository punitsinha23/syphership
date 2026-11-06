import { Link, NavLink } from "react-router-dom"
import { Logo } from "../Logo/Logo"
import { useScrollReveal } from "../../hooks/useScrollReveal"
import "./PublicLayout.css"

// Header and footer shared by the public pages (home, about)
export function PublicLayout({ children }) {
    const revealRef = useScrollReveal()
    const signedIn = Boolean(localStorage.getItem("access_token"))

    return (
        <div className="landing-page" ref={revealRef}>
            <header className="landing-nav">
                <Logo className="landing-logo" size={30} />

                <nav className="landing-nav-links" aria-label="Main">
                    <NavLink to="/how-it-works">How it works</NavLink>
                    <NavLink to="/docs">Docs</NavLink>
                    <Link to="/#security">Security</Link>
                    <NavLink to="/about">About</NavLink>
                </nav>

                <Link className="btn btn-secondary btn-sm" to={signedIn ? "/dashboard" : "/login"}>
                    {signedIn ? "Dashboard" : "Sign in"}
                </Link>
            </header>

            {children}

            <footer className="landing-footer">
                <span>© {new Date().getFullYear()} Syphership · Built by Punit Sinha</span>
                <nav className="landing-footer-links" aria-label="Footer">
                    <Link to="/how-it-works">How it works</Link>
                    <Link to="/docs">Docs</Link>
                    <Link to="/about">About</Link>
                    <Link to="/privacy">Privacy</Link>
                    <Link to="/terms">Terms</Link>
                    <a href="https://github.com/punitsinha23/syphership" target="_blank" rel="noreferrer">Source code</a>
                </nav>
            </footer>
        </div>
    )
}
