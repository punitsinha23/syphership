import { Link } from "react-router-dom"
import { PublicLayout } from "../../components/PublicLayout/PublicLayout"
import "./Legal.css"

function Terms() {
    return (
        <PublicLayout>
            <main className="legal">
                <h1>Terms of Use</h1>
                <p className="legal-updated">Last updated: November 6, 2026</p>

                <p>
                    Syphership is a personal project run by Punit Sinha, offered free of charge to invited users.
                    By using it, you agree to these terms.
                </p>

                <h2>Early-stage service</h2>
                <p>
                    Syphership is experimental. It's provided as is, with no guarantee of uptime, and it may change or
                    shut down at any time. Don't use it for production traffic or sensitive workloads. Keep your own
                    copies of anything important.
                </p>

                <h2>Your code stays yours</h2>
                <p>
                    You keep all rights to your code. You allow Syphership to copy, build and run it, only to provide
                    this service. You're responsible for your apps and for having the right to deploy them.
                </p>

                <h2>What you can't do</h2>
                <ul>
                    <li>Break the law, or host illegal or harmful content.</li>
                    <li>Host malware or phishing pages, or attack other systems.</li>
                    <li>Mine cryptocurrency, send spam, or run anything that overloads the service.</li>
                    <li>Try to escape your container, or reach other users' apps or data.</li>
                    <li>Get around usage limits.</li>
                </ul>
                <p>
                    Found a security problem? Tell me about it before sharing it publicly. Honest reports are welcome.
                </p>

                <h2>Suspension</h2>
                <p>
                    I may stop your apps or remove your account if you break these terms, or if it's needed to protect
                    the service or other users.
                </p>

                <h2>Ending your account</h2>
                <p>You can delete your account at any time from Settings.</p>

                <h2>Liability</h2>
                <p>
                    As far as the law allows, I'm not liable for lost data, downtime, or other damages from using
                    Syphership.
                </p>

                <h2>Changes</h2>
                <p>
                    These terms may change. The date above shows the latest version, and continuing to use Syphership
                    means you accept it.
                </p>

                <h2>Contact</h2>
                <p>
                    Reach me through <a href="https://github.com/punitsinha23" target="_blank" rel="noreferrer">GitHub</a>.
                    See also the <Link to="/privacy">Privacy Policy</Link>.
                </p>
            </main>
        </PublicLayout>
    )
}

export default Terms
