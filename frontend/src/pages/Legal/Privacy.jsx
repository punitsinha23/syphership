import { Link } from "react-router-dom"
import { PublicLayout } from "../../components/PublicLayout/PublicLayout"
import "./Legal.css"

function Privacy() {
    return (
        <PublicLayout>
            <main className="legal">
                <h1>Privacy Policy</h1>
                <p className="legal-updated">Last updated: November 6, 2026</p>

                <p>
                    Syphership is a personal project run by Punit Sinha. This page explains what data it collects, why,
                    and what you can do about it.
                </p>

                <h2>What we collect</h2>
                <ul>
                    <li><strong>Account details:</strong> your email, username and avatar, from GitHub or Google.</li>
                    <li><strong>GitHub access token:</strong> stored encrypted. Google tokens aren't stored.</li>
                    <li><strong>Project details:</strong> the repository, branch and settings of each project.</li>
                    <li><strong>Deployment data:</strong> commit IDs, build logs, status and timing.</li>
                    <li><strong>Environment variables:</strong> stored encrypted.</li>
                    <li><strong>Your code:</strong> cloned for each build and deleted afterwards. The built image stays on the server while the deployment exists.</li>
                    <li><strong>Technical data:</strong> your IP address is used briefly for rate limiting, and may appear in server logs.</li>
                </ul>

                <h2>Why we use it</h2>
                <p>
                    Only to run the service: to sign you in, build and run your apps, show you their status, and protect
                    the service from abuse. We don't sell your data, use it for advertising, or track you with analytics.
                </p>

                <h2>Who else is involved</h2>
                <ul>
                    <li><strong>GitHub and Google,</strong> for sign-in. GitHub also hosts your repositories.</li>
                    <li><strong>The server provider</strong> that hosts Syphership.</li>
                    <li><strong>Google Fonts,</strong> which loads this site's fonts and can see your IP address.</li>
                </ul>
                <p>We may also share data if the law requires it.</p>

                <h2>Browser storage</h2>
                <p>
                    Your sign-in tokens are kept in your browser's local storage. One short-lived cookie protects the
                    sign-in process. There are no advertising cookies.
                </p>

                <h2>How long we keep it</h2>
                <p>
                    We keep your data until you delete it or your account. Backups may keep deleted data for a short
                    time until they're replaced.
                </p>

                <h2>Your choices</h2>
                <ul>
                    <li>Delete a project or deployment at any time.</li>
                    <li>Delete your whole account from Settings.</li>
                    <li>Revoke access from your <a href="https://github.com/settings/applications" target="_blank" rel="noreferrer">GitHub settings</a>.</li>
                    <li>Ask for a copy of your data, or for a correction, by contacting me.</li>
                </ul>

                <h2>Security</h2>
                <p>
                    No service is perfectly secure. <Link to="/how-it-works">How it works</Link> explains how your data
                    is protected, and where the limits are.
                </p>

                <h2>Contact</h2>
                <p>
                    Reach me through <a href="https://github.com/punitsinha23" target="_blank" rel="noreferrer">GitHub</a>.
                </p>
            </main>
        </PublicLayout>
    )
}

export default Privacy
