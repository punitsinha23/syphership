import { useEffect } from "react"
import { Link } from "react-router-dom"
import { PublicLayout } from "../../components/PublicLayout/PublicLayout"
import { reveal } from "../../hooks/useScrollReveal"
import "./HowItWorks.css"

const REPO_URL = "https://github.com/punitsinha23/syphership"

const PIPELINE = ["git push", "GitHub", "API", "Redis", "Worker", "Docker", "Live"]

const JOURNEY = [
    {
        title: "You push code",
        text: "You run git push, and GitHub sends a webhook to Syphership: a message saying which repository, branch and commit changed.",
    },
    {
        title: "The API checks it's real",
        text: "The webhook URL is public, so anyone could call it. GitHub signs each message with a secret only that project has, and the API rejects anything with a wrong signature.",
    },
    {
        title: "The job joins a queue",
        text: "The API saves a deployment and adds it to a queue in Redis, then answers GitHub straight away. A build can take minutes, and nobody should wait on it.",
    },
    {
        title: "A worker picks it up",
        text: "A worker takes the next job. Workers run separately from the API, so more of them means more builds at once. If one dies mid-build, another notices and handles the job.",
    },
    {
        title: "Your code is built",
        text: "The worker clones that exact commit into a temporary folder, runs docker build, and deletes the folder afterwards.",
    },
    {
        title: "Your app starts, locked down",
        text: "The container starts on its own network, with limits on CPU, memory and processes, and it isn't allowed to run as root.",
    },
    {
        title: "It goes live",
        text: "Syphership checks that your app answers. Only then does it replace the previous version, so a broken deploy doesn't take down a working one.",
    },
]

const PARTS = [
    { name: "Frontend", tech: "React", text: "This website. It shows your projects and talks only to the API." },
    { name: "API", tech: "FastAPI", text: "Handles sign-in, permissions and webhooks. It has no access to Docker." },
    { name: "Database", tech: "PostgreSQL", text: "Keeps accounts, projects, deployments and build logs." },
    { name: "Queue", tech: "Redis Streams", text: "Holds jobs until a worker is free, and remembers them across restarts." },
    { name: "Workers", tech: "Python", text: "The only part that touches Docker. They build, run and remove apps." },
    { name: "Your app", tech: "Docker", text: "Runs in its own container, cut off from the database, the queue and the API." },
]

const STORED = [
    { item: "Email, username, avatar", why: "To identify your account", how: "Stored as is" },
    { item: "GitHub access token", why: "To list repositories, clone your code and add the webhook", how: "Encrypted; kept out of build logs and error messages" },
    { item: "Google access token", why: "Used once at sign-in", how: "Not stored" },
    { item: "Repository details", why: "To know what to deploy", how: "Stored as is" },
    { item: "Build logs", why: "So you can see what happened", how: "GitHub tokens are removed before saving" },
    { item: "Environment variables", why: "Your app needs them to run", how: "Encrypted; the API never returns the values" },
    { item: "Webhook secret", why: "To prove a push came from GitHub", how: "Encrypted; a different secret for each project" },
    { item: "Your source code", why: "Only needed during the build", how: "Deleted right after the build. The built image stays while the deployment exists" },
    { item: "Passwords", why: "You sign in with GitHub or Google", how: "None exist" },
]

const PROTECTIONS = [
    { title: "Apps can't reach our systems", text: "Deployed apps run on a separate network, and the database and queue only listen on the server itself." },
    { title: "No root", text: "Images that run as root are refused. All Linux capabilities are dropped, and apps can't gain new privileges." },
    { title: "Limits on every app", text: "CPU, memory and process limits stop one app from starving the others." },
    { title: "Other users can't see your data", text: "Every request checks ownership. Asking for someone else's project gets the same answer as one that doesn't exist." },
    { title: "Signed webhooks", text: "A push only counts if it's signed with that project's secret, and repeated deliveries are ignored." },
    { title: "Rate limits", text: "Sign-in, deploy and webhook routes are limited, so they can't be flooded." },
    { title: "Checked input", text: "Commit IDs and branch names are validated before they reach git or Docker." },
    { title: "The public API has no Docker access", text: "Docker access is the same as full control of the server, so only workers have it, and they accept no requests from the internet." },
]

const LIMITS = [
    {
        title: "The GitHub permission is broad",
        text: "To deploy private repositories, GitHub makes us ask for the repo permission, which covers all your repositories. Syphership uses it to list them, clone the one you deploy, and add a webhook to it. It never pushes code, but you are trusting it with that access.",
    },
    {
        title: "Containers share one kernel",
        text: "Docker keeps apps apart well, but they all run on the same machine. A serious kernel bug could break that wall. That's why the launch will be invite-only.",
    },
    {
        title: "Encryption has a limit",
        text: "Encrypted data protects you if the database leaks. The key lives on the same server, so an attacker with full control of that server could still read it. As the operator, I could too.",
    },
    {
        title: "It's one server, run by one person",
        text: "If the server goes down, every app goes down with it. Don't use Syphership for production traffic or sensitive workloads yet.",
    },
]

const LESSONS = [
    {
        title: "The queue that forgot everything",
        text: "Restarting Redis wiped every waiting job, because it wasn't saving to disk. Turning on its append-only log fixed that.",
    },
    {
        title: "Two workers, one name",
        text: "Each worker needs a unique name in the queue, but my two containers had the same hostname and process ID. They looked like one worker. Adding a random suffix fixed it.",
    },
    {
        title: "The test app that reached Redis",
        text: "I ran an attack from inside a container, and it reached Redis with no password. So I moved apps to their own network and closed those ports, then ran the same attack again to prove it failed.",
    },
]

function HowItWorks() {
    useEffect(() => {
        window.scrollTo(0, 0)
    }, [])

    return (
        <PublicLayout>
            <main className="how">
                <header className="how-hero">
                    <p className="eyebrow" {...reveal(0)}>How it works</p>
                    <h1 className="how-title" {...reveal(80)}>
                        What happens to your code, and why you can{" "}
                        <span className="how-title-accent">trust it.</span>
                    </h1>
                    <p className="how-lead" {...reveal(160)}>
                        You're handing your code to someone else's server, so you should know exactly what it does.
                        This page explains how Syphership works, what it stores, and where its limits are.
                    </p>
                    <ol className="how-pipeline" aria-label="The path of a push" {...reveal(240)}>
                        {PIPELINE.map((name, index) => (
                            <li key={name} style={{ "--step": index }}>{name}</li>
                        ))}
                    </ol>
                </header>

                <section className="how-section" aria-labelledby="journey-heading">
                    <div className="how-intro" {...reveal()}>
                        <p className="eyebrow">Follow one push</p>
                        <h2 id="journey-heading">From git push to a live app</h2>
                    </div>
                    <ol className="how-journey">
                        {JOURNEY.map((step, index) => (
                            <li key={step.title} {...reveal(60)}>
                                <span className="how-journey-index">{String(index + 1).padStart(2, "0")}</span>
                                <div>
                                    <h3>{step.title}</h3>
                                    <p>{step.text}</p>
                                </div>
                            </li>
                        ))}
                    </ol>
                </section>

                <section className="how-section" aria-labelledby="parts-heading">
                    <div className="how-intro" {...reveal()}>
                        <p className="eyebrow">The parts</p>
                        <h2 id="parts-heading">How everything talks to each other</h2>
                        <p>
                            Each part does one job and can only reach what that job needs.
                            If one part is attacked, the damage should stop there.
                        </p>
                    </div>
                    <ul className="how-parts">
                        {PARTS.map((part, index) => (
                            <li key={part.name} className="card" {...reveal(index * 60)}>
                                <h3>{part.name}</h3>
                                <code>{part.tech}</code>
                                <p>{part.text}</p>
                            </li>
                        ))}
                    </ul>
                </section>

                <section className="how-section" aria-labelledby="data-heading">
                    <div className="how-intro" {...reveal()}>
                        <p className="eyebrow">Your data</p>
                        <h2 id="data-heading">What we store, and why</h2>
                    </div>
                    <div className="card how-table-card" {...reveal(80)}>
                        <table className="how-table">
                            <thead>
                                <tr>
                                    <th scope="col">What</th>
                                    <th scope="col">Why</th>
                                    <th scope="col">How it's handled</th>
                                </tr>
                            </thead>
                            <tbody>
                                {STORED.map((row) => (
                                    <tr key={row.item}>
                                        <th scope="row">{row.item}</th>
                                        <td data-label="Why">{row.why}</td>
                                        <td data-label="How it's handled">{row.how}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </section>

                <section className="how-section" aria-labelledby="protect-heading">
                    <div className="how-intro" {...reveal()}>
                        <p className="eyebrow">Protection</p>
                        <h2 id="protect-heading">How your apps and data are protected</h2>
                        <p>
                            Syphership runs code from strangers, so it treats every deployed app as possibly hostile.
                            The full threat model is in the{" "}
                            <a href={`${REPO_URL}/blob/main/docs/SECURITY.md`} target="_blank" rel="noreferrer">
                                security document
                            </a>.
                        </p>
                    </div>
                    <ul className="how-grid">
                        {PROTECTIONS.map((item, index) => (
                            <li key={item.title} {...reveal((index % 2) * 80)}>
                                <h3>{item.title}</h3>
                                <p>{item.text}</p>
                            </li>
                        ))}
                    </ul>
                </section>

                <section className="how-section" aria-labelledby="limits-heading">
                    <div className="how-intro" {...reveal()}>
                        <p className="eyebrow">The honest part</p>
                        <h2 id="limits-heading">What we don't protect against yet</h2>
                        <p>No system is perfectly safe. These are the limits you should know before you use this one.</p>
                    </div>
                    <ul className="how-limits">
                        {LIMITS.map((item, index) => (
                            <li key={item.title} className="card" {...reveal((index % 2) * 80)}>
                                <h3>{item.title}</h3>
                                <p>{item.text}</p>
                            </li>
                        ))}
                    </ul>
                </section>

                <section className="how-section" aria-labelledby="built-heading">
                    <div className="how-intro" {...reveal()}>
                        <p className="eyebrow">Behind the scenes</p>
                        <h2 id="built-heading">How I built it</h2>
                        <p>
                            I built Syphership to understand what really happens between a git push and a live URL.
                            I started with a basic API, then added GitHub sign-in, real Docker deployments,
                            a job queue with scalable workers, and security hardening, one phase at a time.
                            Here are a few things that went wrong along the way.
                        </p>
                    </div>
                    <ul className="how-grid how-grid-three">
                        {LESSONS.map((item, index) => (
                            <li key={item.title} {...reveal(index * 80)}>
                                <h3>{item.title}</h3>
                                <p>{item.text}</p>
                            </li>
                        ))}
                    </ul>
                    <p className="how-more" {...reveal()}>
                        All of the code is public, so you can check any of this yourself:{" "}
                        <a href={REPO_URL} target="_blank" rel="noreferrer">read the source</a>.
                    </p>
                </section>

                <section className="how-section" aria-labelledby="control-heading">
                    <div className="how-intro" {...reveal()}>
                        <p className="eyebrow">You're in control</p>
                        <h2 id="control-heading">Removing your data</h2>
                    </div>
                    <ul className="how-control" {...reveal(80)}>
                        <li>
                            <strong>Delete a project</strong> and its containers, images, build logs,
                            environment variables and webhook are removed.
                        </li>
                        <li>
                            <strong>Revoke access</strong> at any time from your{" "}
                            <a href="https://github.com/settings/applications" target="_blank" rel="noreferrer">
                                GitHub settings
                            </a>. It takes effect immediately.
                        </li>
                        <li>
                            <strong>Delete your account:</strong> there's no button for this yet.
                            Contact me through{" "}
                            <a href="https://github.com/punitsinha23" target="_blank" rel="noreferrer">GitHub</a>{" "}
                            and I'll do it for you.
                        </li>
                        <li>
                            <strong>Found a security problem?</strong> Please tell me the same way, before posting
                            the details publicly.
                        </li>
                    </ul>
                    <p className="how-more" {...reveal()}>
                        Want to know who's behind this? <Link to="/about">Read about the project</Link>.
                    </p>
                </section>
            </main>
        </PublicLayout>
    )
}

export default HowItWorks
