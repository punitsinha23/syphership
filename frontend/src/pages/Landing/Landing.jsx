import { useLocation, useNavigate } from "react-router-dom"
import { useEffect } from "react"
import { OAuthButtons } from "../../components/OAuthButtons/OAuthButtons"
import { PublicLayout } from "../../components/PublicLayout/PublicLayout"
import { reveal } from "../../hooks/useScrollReveal"
import "./Landing.css"

const STEPS = [
    {
        step: "01",
        title: "Sign in",
        text: "Use GitHub or Google. No new password to create or remember.",
    },
    {
        step: "02",
        title: "Pick a repository",
        text: "Choose a repo and branch. It needs a Dockerfile at its root.",
    },
    {
        step: "03",
        title: "We build it",
        text: "Syphership clones the latest commit, runs docker build and keeps the full build log.",
    },
    {
        step: "04",
        title: "It goes live",
        text: "Your container starts, we check that it answers, and you get a URL.",
    },
]

// Exactly what each sign-in provider is asked for (see github/service.py, google_oauth/service.py)
const PERMISSIONS = [
    {
        provider: "GitHub",
        scopes: [
            { name: "read:user", text: "Your public profile: name, username and avatar." },
            { name: "user:email", text: "Your email address, to identify your account." },
            {
                name: "repo",
                text: "Lets us list your repositories and clone the one you deploy, including private ones.",
            },
        ],
        note:
            "GitHub labels the repo permission as full access, because it has no read-only option for " +
            "private code. Syphership only reads: it never pushes, commits, opens pull requests or changes settings.",
    },
    {
        provider: "Google",
        scopes: [
            { name: "openid · email · profile", text: "Your name, email address and profile picture." },
        ],
        note: "Nothing else. No access to Gmail, Drive, Calendar or any other Google data.",
    },
]

const PRACTICES = [
    {
        title: "No passwords",
        text: "You sign in through GitHub or Google, so Syphership never sees or stores a password.",
    },
    {
        title: "Encrypted tokens",
        text: "Your GitHub access token is encrypted before it is saved, and only decrypted when Syphership talks to GitHub for you.",
    },
    {
        title: "Only what you deploy",
        text: "We clone the single repository and branch you choose, at the exact commit being deployed.",
    },
    {
        title: "Source deleted after build",
        text: "The temporary copy of your code is removed as soon as the build finishes.",
    },
    {
        title: "Isolated containers",
        text: "Every deployment runs in its own Docker container, separate from other apps.",
    },
    {
        title: "You stay in control",
        text: "Deleting a deployment or project removes its containers, images and build logs.",
    },
]

const FAQ = [
    {
        question: "Why does GitHub say Syphership can access all my repositories?",
        answer:
            "GitHub's sign-in lets apps ask for public-only access or for full repository access. To deploy " +
            "private repositories we have to ask for full access, and GitHub shows the broadest description of it. " +
            "Syphership only uses it to list your repositories and to clone the one you deploy.",
    },
    {
        question: "Do you keep a copy of my code?",
        answer:
            "The source is cloned into a temporary folder for the build and deleted right after. The resulting " +
            "Docker image stays on the server while the deployment exists, because that is what runs your app. " +
            "Deleting the deployment removes it.",
    },
    {
        question: "What does my project need?",
        answer:
            "A Dockerfile at the root of the repository that EXPOSEs the port your app listens on. Make sure the " +
            "app listens on 0.0.0.0, not localhost, so it can be reached from outside its container.",
    },
    {
        question: "How do I remove Syphership's access?",
        answer:
            "Delete your projects in Syphership, then revoke access from your GitHub or Google settings (links " +
            "below). Revoking takes effect immediately.",
    },
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

function CheckIcon() {
    return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M5 12l5 5 9-10" />
        </svg>
    )
}

function Landing() {
    const navigate = useNavigate()
    const { hash } = useLocation()

    useEffect(() => {
        const token = localStorage.getItem("access_token")
        if (token) {
            navigate("/dashboard")
        }
    }, [navigate])

    // Links like /#security come from other pages; scroll to the section
    useEffect(() => {
        if (hash) {
            document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" })
        }
    }, [hash])

    return (
        <PublicLayout>
            <main>
                <section className="landing-hero">
                    <div className="landing-hero-text">
                        <p className="eyebrow" {...reveal(0)}>Deploy from GitHub</p>
                        <h1 className="landing-title" {...reveal(80)}>
                            Ship your code<br />into <span className="landing-title-accent">orbit.</span>
                        </h1>
                        <p className="landing-subtitle" {...reveal(160)}>
                            Connect a GitHub repository and Syphership builds it with Docker, runs it,
                            and gives you a live URL. No servers to configure.
                        </p>

                        <div className="landing-auth" {...reveal(240)}>
                            <OAuthButtons />
                        </div>

                        <ul className="landing-trust" aria-label="Security at a glance" {...reveal(320)}>
                            <li><CheckIcon /> No passwords</li>
                            <li><CheckIcon /> Encrypted access tokens</li>
                            <li><CheckIcon /> Revoke access anytime</li>
                        </ul>
                    </div>

                    <div className="landing-hero-visual" {...reveal(200)}>
                        <OrbitVisual />
                    </div>
                </section>

                <section id="how-it-works" className="landing-section" aria-labelledby="how-heading">
                    <p className="eyebrow" {...reveal()}>How it works</p>
                    <h2 id="how-heading" className="landing-section-title" {...reveal(80)}>From commit to live URL in four steps</h2>

                    <ol className="lifecycle-steps">
                        {STEPS.map((item, index) => (
                            <li key={item.step} className="lifecycle-step" {...reveal(120 + index * 100)}>
                                <span className="lifecycle-dot" aria-hidden="true" />
                                <span className="lifecycle-index">{item.step}</span>
                                <h3>{item.title}</h3>
                                <p>{item.text}</p>
                            </li>
                        ))}
                    </ol>
                </section>

                <section id="security" className="landing-section" aria-labelledby="security-heading">
                    <p className="eyebrow" {...reveal()}>Security &amp; privacy</p>
                    <h2 id="security-heading" className="landing-section-title" {...reveal(80)}>
                        What Syphership can access, and why
                    </h2>
                    <p className="landing-section-lead" {...reveal(160)}>
                        Giving an app access to your code is a big decision. Here is every permission we ask for,
                        in plain words, and what we do with it.
                    </p>

                    <div className="permission-grid">
                        {PERMISSIONS.map((group, index) => (
                            <article key={group.provider} className="card permission-card" {...reveal(index * 120)}>
                                <h3>{group.provider}</h3>
                                <dl className="permission-list">
                                    {group.scopes.map((scope) => (
                                        <div key={scope.name} className="permission-item">
                                            <dt><code>{scope.name}</code></dt>
                                            <dd>{scope.text}</dd>
                                        </div>
                                    ))}
                                </dl>
                                <p className="permission-note">{group.note}</p>
                            </article>
                        ))}
                    </div>

                    <ul className="practice-grid">
                        {PRACTICES.map((item, index) => (
                            <li key={item.title} className="practice" {...reveal((index % 3) * 90)}>
                                <span className="practice-icon" aria-hidden="true"><CheckIcon /></span>
                                <div>
                                    <h3>{item.title}</h3>
                                    <p>{item.text}</p>
                                </div>
                            </li>
                        ))}
                    </ul>

                    <p className="revoke-links" {...reveal()}>
                        Revoke access anytime:{" "}
                        <a href="https://github.com/settings/applications" target="_blank" rel="noreferrer">GitHub settings</a>
                        {" · "}
                        <a href="https://myaccount.google.com/connections" target="_blank" rel="noreferrer">Google account</a>
                    </p>
                </section>

                <section className="landing-section" aria-labelledby="faq-heading">
                    <p className="eyebrow" {...reveal()}>Questions</p>
                    <h2 id="faq-heading" className="landing-section-title" {...reveal(80)}>Before you connect</h2>

                    <div className="faq">
                        {FAQ.map((item, index) => (
                            <details key={item.question} className="faq-item" {...reveal(120 + index * 70)}>
                                <summary>{item.question}</summary>
                                <p>{item.answer}</p>
                            </details>
                        ))}
                    </div>
                </section>

                <section className="landing-cta" aria-labelledby="cta-heading" {...reveal()}>
                    <div>
                        <h2 id="cta-heading">Ready for launch?</h2>
                        <p>Either button creates your account in a few seconds.</p>
                    </div>
                    <div className="landing-cta-auth">
                        <OAuthButtons />
                    </div>
                </section>
            </main>
        </PublicLayout>
    )
}

export default Landing
