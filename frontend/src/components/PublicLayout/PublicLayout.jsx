import { Link, NavLink } from "react-router-dom"
import { useScrollReveal } from "../../hooks/useScrollReveal"
import "./PublicLayout.css"

// Header and footer shared by the public pages (home, about)
export function PublicLayout({ children }) {
    const revealRef = useScrollReveal()

    return (
        <div className="landing-page" ref={revealRef}>
            <header className="landing-nav">
                <Link className="landing-logo" to="/" aria-label="Syphership home">
                    <span>SYPHER</span>
                    <span className="landing-logo-accent">//</span>
                    <span>SHIP</span>
                </Link>

                <nav className="landing-nav-links" aria-label="Main">
                    <Link to="/#how-it-works">How it works</Link>
                    <Link to="/#security">Security</Link>
                    <NavLink to="/about">About</NavLink>
                </nav>

                <Link className="btn btn-secondary btn-sm" to="/login">Sign in</Link>
            </header>

            {children}

            <footer className="landing-footer">
                <span>© {new Date().getFullYear()} Syphership · Built by Punit Sinha</span>
                <nav className="landing-footer-links" aria-label="Footer">
                    <Link to="/#security">Security</Link>
                    <Link to="/about">About</Link>
                    <a href="https://github.com/punitsinha23" target="_blank" rel="noreferrer">GitHub</a>
                </nav>
            </footer>
        </div>
    )
}
