import { Link } from "react-router-dom"
import { PublicLayout } from "../../components/PublicLayout/PublicLayout"
import "./Docs.css"

const NODE_DOCKERFILE = `FROM node:22-alpine
WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev
COPY . .

# Give the non-root user the app's files
RUN chown -R node:node /app
USER node

EXPOSE 3000
CMD ["node", "server.js"]`

const PYTHON_DOCKERFILE = `FROM python:3.13-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Create a non-root user and give it the app's files
RUN useradd --create-home app && chown -R app:app /app
USER app

EXPOSE 8000
CMD ["gunicorn", "myproject.wsgi:application", "--bind", "0.0.0.0:8000"]`

const STATIC_DOCKERFILE = `FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# The normal nginx image runs as root and won't start here
FROM nginxinc/nginx-unprivileged:alpine
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080`

const SECTIONS = [
    { id: "start", title: "Getting started" },
    { id: "dockerfile", title: "Dockerfile rules" },
    { id: "examples", title: "Example Dockerfiles" },
    { id: "env", title: "Environment variables" },
    { id: "auto-deploy", title: "Deploy on push" },
    { id: "limits", title: "Limits" },
    { id: "errors", title: "Common errors" },
]

const LIMITS = [
    ["Apps per account", "3"],
    ["CPU per app", "0.5 of a core"],
    ["Memory per app", "256 MB"],
    ["Processes per app", "256"],
    ["Build time", "10 minutes"],
    ["Image size", "2 GB"],
    ["Repository size", "500 MB"],
    ["Environment variables", "50 per project"],
]

const ERRORS = [
    {
        message: "Your app must not run as root.",
        fix: "Add a USER line to your Dockerfile, after giving that user its files. See the examples above.",
    },
    {
        message: "No Dockerfile found at the repository root.",
        fix: "Add a file named Dockerfile to the top folder of your repository, on the branch you deploy.",
    },
    {
        message: "Your Dockerfile must EXPOSE the port your app listens on.",
        fix: "Add a line like EXPOSE 3000, using your app's port.",
    },
    {
        message: "The app did not respond within 60 seconds.",
        fix: "Make your app listen on 0.0.0.0, not localhost or 127.0.0.1, and on the port you EXPOSE. It must answer at the / path without a server error.",
    },
    {
        message: "The container exited right after starting.",
        fix: "Your CMD must keep running. Check for a crash at startup, or for files your non-root user can't write to.",
    },
    {
        message: "Docker build failed.",
        fix: "Open the deployment and read the build log. The real error is near the end.",
    },
    {
        message: "The image is larger than the 2048 MB limit.",
        fix: "Use a slim base image, add a .dockerignore file, and don't copy build tools into the final image.",
    },
    {
        message: "You can have 3 apps running.",
        fix: "Delete a project or a running deployment, then deploy again.",
    },
]

function Docs() {
    return (
        <PublicLayout>
            <main className="docs">
                <header className="docs-hero">
                    <p className="eyebrow">Docs</p>
                    <h1 className="docs-title">Deploy your app on Syphership</h1>
                    <p className="docs-lead">
                        Everything your project needs, and how to fix it when a deployment fails.
                    </p>
                </header>

                <div className="docs-layout">
                    <nav className="docs-nav" aria-label="On this page">
                        {SECTIONS.map((section) => (
                            <a key={section.id} href={`#${section.id}`}>{section.title}</a>
                        ))}
                    </nav>

                    <div className="docs-content">
                        <section id="start">
                            <h2>Getting started</h2>
                            <ol>
                                <li>Sign in with GitHub. If you signed in with Google, connect GitHub from Settings.</li>
                                <li>Add a Dockerfile to your repository, following the rules below.</li>
                                <li>Go to Projects, pick your repository and branch, and create the project.</li>
                                <li>Your first deployment starts by itself. Open it to follow the build.</li>
                            </ol>
                        </section>

                        <section id="dockerfile">
                            <h2>Dockerfile rules</h2>
                            <p>Syphership builds any language, as long as your Dockerfile follows four rules:</p>
                            <ul>
                                <li><strong>It's at the top of your repository,</strong> and named <code>Dockerfile</code>.</li>
                                <li><strong>It has an <code>EXPOSE</code> line</strong> with the port your app uses. If there are several, the lowest is used.</li>
                                <li><strong>It sets a non-root <code>USER</code>.</strong> Apps that run as root are refused.</li>
                                <li><strong>Your app listens on <code>0.0.0.0</code>,</strong> not <code>localhost</code>. Otherwise nothing outside the container can reach it.</li>
                            </ul>
                            <p>
                                Use a port of 1024 or higher. Your app's user must own any files it writes to,
                                which is why the examples below run <code>chown</code> before <code>USER</code>.
                            </p>
                        </section>

                        <section id="examples">
                            <h2>Example Dockerfiles</h2>
                            <h3>Node.js</h3>
                            <pre><code>{NODE_DOCKERFILE}</code></pre>
                            <h3>Python (Django)</h3>
                            <pre><code>{PYTHON_DOCKERFILE}</code></pre>
                            <h3>Static site or React app</h3>
                            <pre><code>{STATIC_DOCKERFILE}</code></pre>
                        </section>

                        <section id="env">
                            <h2>Environment variables</h2>
                            <p>
                                Add API keys and other settings in your project's Settings section. Values are encrypted
                                and can't be viewed after saving. Changes apply from the next deployment.
                            </p>
                            <p>
                                They're available while your app runs, not during the Docker build. Don't put secrets
                                in your Dockerfile or repository.
                            </p>
                        </section>

                        <section id="auto-deploy">
                            <h2>Deploy on push</h2>
                            <p>
                                When you link a repository, Syphership adds a webhook to it, so each push to your
                                branch deploys automatically. You need admin access to the repository for this. Without
                                it, deploy with the Deploy button. You can turn this off in your project's Settings.
                            </p>
                            <p>
                                A push that arrives during a build is skipped, so that commit won't go live until
                                your next push or a manual deploy.
                            </p>
                        </section>

                        <section id="limits">
                            <h2>Limits</h2>
                            <table>
                                <tbody>
                                    {LIMITS.map(([name, value]) => (
                                        <tr key={name}>
                                            <th scope="row">{name}</th>
                                            <td>{value}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            <p>
                                <strong>Files don't survive a deploy.</strong> Each deployment starts a new container, so
                                anything your app saved to disk is gone, including a SQLite database. Syphership has no
                                storage or database service yet, so use an external database for data you need to keep.
                            </p>
                        </section>

                        <section id="errors">
                            <h2>Common errors</h2>
                            <dl>
                                {ERRORS.map((error) => (
                                    <div key={error.message}>
                                        <dt>{error.message}</dt>
                                        <dd>{error.fix}</dd>
                                    </div>
                                ))}
                            </dl>
                            <p>
                                Curious what happens behind the scenes? Read{" "}
                                <Link to="/how-it-works">how Syphership works</Link>.
                            </p>
                        </section>
                    </div>
                </div>
            </main>
        </PublicLayout>
    )
}

export default Docs
