# Syphership Security Model

Syphership builds and runs code written by its users on our machine. The main question for every part of the system is: **if someone deploys an app written to cause harm, what can it reach?**

Status: ✅ done · 🟡 partial · ❌ open

**Last updated:** 2026-11-04

---

## Assets

| Asset | Why it matters |
|---|---|
| **PostgreSQL** | Users, projects, deployments, and every user's encrypted GitHub token. |
| **OAuth tokens** | A GitHub token with `repo` scope can read and push to the user's repositories. |
| **The host / Docker socket** | Anyone who can talk to the Docker socket can run `docker run -v /:/host ...` and become root on the host. |
| **Redis** | The deployment queue. Whoever can write to it can delete queued jobs or publish fake ones (redeploying other users' apps). |
| **Project secrets** | Webhook secrets and app environment variables, encrypted in PostgreSQL. |
| **Other users' apps** | One user's app must not read, disrupt or starve another's. |
| **`SECRET_KEY`** | Signs session JWTs and derives the token encryption key. Leaking it breaks both. |

## Attackers

1. **Malicious repo owner** — a logged-in user who deploys code written to attack the platform.
2. **Another logged-in user** — tries to read or change projects and deployments that aren't theirs.
3. **Anyone on the internet** — no account; can send requests to public endpoints.

---

## Attacks and mitigations

| # | Attack | Attacker | Mitigation | Status |
|---|---|---|---|---|
| 1 | Deployed app connects to Redis/Postgres through the host gateway (`172.17.0.1`) | 1 | Postgres and Redis published on `127.0.0.1` only; apps run on their own network `syphership-apps` | ✅ |
| 2 | Deployed app uses root powers or escapes the container | 1 | Apps must run as non-root: images with no `USER` or with root are refused, and any process really running as UID 0 fails the deployment (`docker top`, which also catches another username with UID 0). `--cap-drop ALL` and `--security-opt no-new-privileges` stop a non-root process becoming root; no volumes or Docker socket mounted into apps | ✅ |
| 3 | App uses all CPU/memory/processes and starves the host | 1 | `--cpus 0.5`, `--memory 256m`, `--memory-swap 256m`, `--pids-limit 256` | ✅ |
| 4 | User reads another user's project/deployment/logs by changing the ID in the URL (IDOR) | 2 | Every query filters by `Project.user_id == user.id`; returns 404 (not 403) so IDs can't be probed | ✅ |
| 5 | Repo, branch or SHA used to inject shell commands or git options | 1 | All `subprocess` calls use argument lists, never `shell=True`; clone only accepts HTTPS `github.com` URLs ending in `.git`; SHAs must be 40 lowercase hex characters; repo names must be `owner/name`; branch names can't start with `-` or hold characters git refuses | ✅ |
| 6 | GitHub token leaks via `git remote -v`, clone errors or build logs | 1/2 | Token passed to git as an HTTP header through environment variables, never in the URL; clone errors shown to users are generic; build logs and failure reasons go through `scrub()` before saving, with tests that try to leak a token | ✅ |
| 7 | Database dump exposes OAuth tokens | 3 | Tokens encrypted at rest with Fernet (key derived from `SECRET_KEY`) | ✅ |
| 8 | Forged request pretending to be a GitHub push | 3 | Each project has its own random secret, stored encrypted; `X-Hub-Signature-256` checked with HMAC-SHA256 and `hmac.compare_digest`; repeated `X-GitHub-Delivery` IDs ignored for 24 hours | ✅ |
| 9 | Brute force or spam on login, deploy, webhook | 3 | Fixed-window counters in Redis: deploy 5/min per user; login exchange 10/min, token refresh 30/min and webhook 60/min per IP. Over the limit returns 429; if Redis is down, these routes return 503 | ✅ |
| 10 | A broken or hostile queue message crashes the workers in a loop | 1/3 | Malformed messages and messages delivered `MAX_DELIVERIES` times go to the dead-letter stream | ✅ |
| 11 | Docker socket access from the API | 3 | Only workers use Docker. The API queues cleanup jobs when a deployment or project is deleted, and a test checks it never loads the Docker code | ✅ |

### Evidence

**#1 — network isolation.** From a throwaway container (the same kind a user's app runs in):

```text
Before:  redis-cli -h 172.17.0.1 PING          → PONG   (full access, no password)
         pg_isready -h 172.17.0.1 -p 5435      → accepting connections
After:   redis-cli -h 172.17.0.1 PING          → Connection refused
         pg_isready -h 172.17.0.1 -p 5435      → no response
```

From inside a real deployment on `syphership-apps`, connections to `172.20.0.1` (its gateway) and `172.17.0.1` on ports 6379 and 5435 are blocked.

**#2 — capabilities dropped.** Inside a deployed container running as root:

```text
chown 1:1 /www/index.html  → Operation not permitted
```

**#2 — root refused.** Against real Docker images:

```text
Djangotodo (USER app)                  → allowed
nginx (no USER, runs as root)          → refused by the image check
USER toor, with UID 0 in /etc/passwd   → passes the image check, refused by the running check
```

---

## Open work

- **#2 Stronger isolation:** containers share the host kernel, so Docker alone is not strong isolation for untrusted code. Launch is invite-only. Consider gVisor or user namespace remapping on the server.
- **Tokens:** access tokens last 1 hour and refresh tokens 7 days. Refresh token rotation is not built yet (Phase 7).
- **Env vars:** values are encrypted at rest and never returned by the API, but they are visible to the host through `docker inspect` and in the worker's `docker run` arguments.
- **#6 Server logs:** tracebacks from unexpected errors (`logger.exception`) are not scrubbed. Users never see them, but anyone reading the worker logs could.
- **#7 Key separation:** use a dedicated encryption key instead of deriving it from `SECRET_KEY`, so rotating one doesn't break the other.
- **#9 Client IP behind a proxy:** once Caddy is in front (Phase 7), `request.client.host` will be Caddy's IP, so read the real one from a trusted header.
- **Redis password:** add `--requirepass` as a second layer behind #1.
