import { Link, useNavigate } from "react-router-dom"
import { useEffect } from "react"
import { OAuthButtons } from "../../components/OAuthButtons/OAuthButtons"
import "./Landing.css"

const LIFECYCLE = [
    { step: "01", title: "Build", text: "Compile your application from any commit." },
    { step: "02", title: "Deploy", text: "Ship it to production with one click." },
    { step: "03", title: "Run", text: "Monitor every deployment as it goes live." },
]

const reduceMotion =
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches

// Thin orbital rings with a single cyan point travelling along the outer orbit
function OrbitVisual() {
    const outer = "M 30 200 a 170 66 0 1 0 340 0 a 170 66 0 1 0 -340 0"

    return (
        <svg className="landing-orbit" viewBox="0 0 400 400" role="img" aria-label="Orbit illustration">
            <defs>
                <radialGradient id="orbit-core" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#67e8f9" stopOpacity="0.9" />
                    <stop offset="100%" stopColor="#22d3ee" stopOpacity="0" />
                </radialGradient>
            </defs>

            <circle cx="200" cy="200" r="188" className="orbit-ring orbit-ring-faint" />

            <g transform="rotate(-18 200 200)">
                <ellipse cx="200" cy="200" rx="170" ry="66" className="orbit-ring" />
                <ellipse cx="200" cy="200" rx="112" ry="42" className="orbit-ring orbit-ring-faint" />

                <circle cx="30" cy="200" r="3" className="orbit-marker" />
                <circle cx="200" cy="134" r="3" className="orbit-marker" />
                <circle cx="370" cy="200" r="3" className="orbit-marker" />

                <circle r="5" className="orbit-point">
                    {!reduceMotion && (
                        <animateMotion dur="14s" repeatCount="indefinite" path={outer} />
                    )}
                </circle>
            </g>

            <circle cx="200" cy="200" r="34" fill="url(#orbit-core)" opacity="0.35" />
            <circle cx="200" cy="200" r="7" className="orbit-core" />

            <text x="14" y="282" className="orbit-label">BUILD</text>
            <text x="164" y="118" className="orbit-label">DEPLOY</text>
            <text x="338" y="168" className="orbit-label">RUN</text>
        </svg>
    )
}

function Landing() {
    const navigate = useNavigate()

    useEffect(() => {
        const token = localStorage.getItem("access_token")
        if (token) {
            navigate("/dashboard")
        }
    }, [navigate])

    return (
        <div className="landing-page">
            <header className="landing-nav">
                <span className="landing-logo">
                    <span>SYPHER</span>
                    <span className="landing-logo-accent">//</span>
                    <span>SHIP</span>
                </span>
                <Link className="btn btn-secondary btn-sm" to="/login">Sign in</Link>
            </header>

            <main>
                <section className="landing-hero">
                    <div className="landing-hero-text">
                        <p className="eyebrow">Deployment platform</p>
                        <h1 className="landing-title">
                            Ship your code<br />into <span className="landing-title-accent">orbit.</span>
                        </h1>
                        <p className="landing-subtitle">
                            Build, deploy, and monitor your applications from one place.
                        </p>

                        <div className="landing-auth">
                            <OAuthButtons />
                        </div>
                    </div>

                    <div className="landing-hero-visual">
                        <OrbitVisual />
                    </div>
                </section>

                <section className="landing-lifecycle" aria-labelledby="lifecycle-heading">
                    <p id="lifecycle-heading" className="eyebrow">From commit to production</p>

                    <ol className="lifecycle-steps">
                        {LIFECYCLE.map((item) => (
                            <li key={item.step} className="lifecycle-step">
                                <span className="lifecycle-dot" aria-hidden="true" />
                                <span className="lifecycle-index">{item.step}</span>
                                <h2>{item.title}</h2>
                                <p>{item.text}</p>
                            </li>
                        ))}
                    </ol>
                </section>
            </main>

            <footer className="landing-footer">
                <span>© {new Date().getFullYear()} Syphership</span>
                <span className="mono">SYPHER//SHIP</span>
            </footer>
        </div>
    )
}

export default Landing
