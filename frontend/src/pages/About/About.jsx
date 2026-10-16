import { Link } from "react-router-dom"
import { PublicLayout } from "../../components/PublicLayout/PublicLayout"
import { reveal } from "../../hooks/useScrollReveal"
import "./About.css"

const TODAY = [
    "Sign in with GitHub or Google",
    "Deploy any repository that has a Dockerfile",
    "Run each deployment in its own container, with a health check",
    "Follow status live and read the full build log",
    "Delete deployments and projects, containers included",
]

// From the project roadmap (PROJECT.md)
const NEXT = [
    "A job queue with separate build workers",
    "Stable URLs per project and custom domains",
    "Environment variables and secrets",
    "Live log streaming while a build runs",
]

const PRINCIPLES = [
    {
        title: "Explain every permission",
        text: "If Syphership asks for access, the reason is written down on the homepage in plain words.",
    },
    {
        title: "Read, never write",
        text: "Syphership reads the repository you deploy. It never pushes, commits or changes anything on GitHub.",
    },
    {
        title: "Be honest about limits",
        text: "This page says what works today and what does not yet, instead of promising more than exists.",
    },
]

const STACK = ["React", "FastAPI", "PostgreSQL", "Docker"]

function About() {
    return (
        <PublicLayout>
            <main className="about">
                <header className="about-hero">
                    <p className="eyebrow" {...reveal(0)}>About Syphership</p>
                    <h1 className="about-title" {...reveal(80)}>
                        Built by one developer, to understand how deployment{" "}
                        <span className="about-title-accent">really works.</span>
                    </h1>
                    <p className="about-lead" {...reveal(160)}>
                        Syphership is a personal project by Punit Sinha. It is built to learn how platforms
                        like Vercel, Render and Railway work under the hood, by building one step by step:
                        from a git commit to a container running at a live URL.
                    </p>
                </header>

                <section className="about-section about-status" aria-labelledby="status-heading">
                    <div className="about-section-intro" {...reveal()}>
                        <p className="eyebrow">Where it stands</p>
                        <h2 id="status-heading">Early stage, and honest about it</h2>
                        <p>
                            Syphership already deploys real applications, but it is young. Please don't use it
                            for production traffic or sensitive workloads yet.
                        </p>
                    </div>

                    <div className="about-columns">
                        <div className="card about-list-card" {...reveal(100)}>
                            <h3>Works today</h3>
                            <ul className="about-list about-list-done">
                                {TODAY.map((item) => <li key={item}>{item}</li>)}
                            </ul>
                        </div>
                        <div className="card about-list-card" {...reveal(200)}>
                            <h3>Coming next</h3>
                            <ul className="about-list about-list-next">
                                {NEXT.map((item) => <li key={item}>{item}</li>)}
                            </ul>
                        </div>
                    </div>
                </section>

                <section className="about-section" aria-labelledby="principles-heading">
                    <div className="about-section-intro" {...reveal()}>
                        <p className="eyebrow">Principles</p>
                        <h2 id="principles-heading">How Syphership treats your trust</h2>
                    </div>

                    <ol className="about-principles">
                        {PRINCIPLES.map((item, index) => (
                            <li key={item.title} {...reveal(100 + index * 100)}>
                                <span className="about-principle-index">0{index + 1}</span>
                                <h3>{item.title}</h3>
                                <p>{item.text}</p>
                            </li>
                        ))}
                    </ol>

                    <p className="about-more" {...reveal()}>
                        Every permission is listed on the <Link to="/#security">security section</Link> of the homepage.
                    </p>
                </section>

                <section className="about-section about-maker" aria-labelledby="maker-heading">
                    <div className="card about-maker-card" {...reveal()}>
                        <span className="about-avatar" aria-hidden="true">PS</span>
                        <div className="about-maker-text">
                            <p className="eyebrow">The developer</p>
                            <h2 id="maker-heading">Punit Sinha</h2>
                            <p>
                                Solo developer building Syphership from the ground up: the API, the build
                                pipeline and this interface.
                            </p>
                            <ul className="about-stack" aria-label="Built with">
                                {STACK.map((item) => <li key={item}>{item}</li>)}
                            </ul>
                        </div>
                        <a
                            className="btn btn-secondary about-maker-link"
                            href="https://github.com/punitsinha23"
                            target="_blank"
                            rel="noreferrer"
                        >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                            </svg>
                            github.com/punitsinha23
                        </a>
                    </div>
                </section>
            </main>
        </PublicLayout>
    )
}

export default About
