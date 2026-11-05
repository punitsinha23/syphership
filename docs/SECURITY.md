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
| 2 | Deployed app uses root powers or escapes the container | 1 | `--cap-drop ALL`, `--security-opt no-new-privileges`; no volumes or Docker socket mounted into apps | 🟡 |
| 3 | App uses all CPU/memory/processes and starves the host | 1 | `--cpus 0.5`, `--memory 256m`, `--memory-swap 256m`, `--pids-limit 256` | ✅ |
| 4 | User reads another user's project/deployment/logs by changing the ID in the URL (IDOR) | 2 | Every query filters by `Project.user_id == user.id`; returns 404 (not 403) so IDs can't be probed | ✅ |
| 5 | Repo, branch or SHA used to inject shell commands or git options | 1 | All `subprocess` calls use argument lists, never `shell=True`; clone only accepts HTTPS `github.com` URLs ending in `.git`; SHAs must be 40 lowercase hex characters; repo names must be `owner/name`; branch names can't start with `-` or hold characters git refuses | ✅ |
| 6 | GitHub token leaks via `git remote -v` or clone errors | 1/2 | Token passed to git as an HTTP header through environment variables, never in the URL | 🟡 |
| 7 | Database dump exposes OAuth tokens | 3 | Tokens encrypted at rest with Fernet (key derived from `SECRET_KEY`) | ✅ |
| 8 | Forged request pretending to be a GitHub push | 3 | — (webhook not built yet) | ❌ |
| 9 | Brute force or spam on login, deploy, webhook | 3 | — | ❌ |
| 10 | A broken or hostile queue message crashes the workers in a loop | 1/3 | Malformed messages and messages delivered `MAX_DELIVERIES` times go to the dead-letter stream | ✅ |
| 11 | Docker socket access from the API | 3 | Builds run only in workers; the API still calls `docker rm` when a deployment is deleted | 🟡 |

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

---

## Open work

- **#2 Non-root:** decide whether to enforce `--user` (breaks images that bind port 80 or write to `/root`). Consider a read-only root filesystem.
- **#6 Scrubbing:** replace tokens with `***` in build logs and error messages before saving; add a test that tries to leak one. Private-repo cloning failed during testing and needs investigating.
- **#7 Key separation:** use a dedicated encryption key instead of deriving it from `SECRET_KEY`, so rotating one doesn't break the other.
- **#8 Webhook:** verify `X-Hub-Signature-256` (HMAC-SHA256, `hmac.compare_digest`); reject repeated `X-GitHub-Delivery` IDs (stored in Redis with a TTL).
- **#9 Rate limiting:** per user/IP counters in Redis with `INCR` + `EXPIRE`; respond 429 over the limit.
- **#11 Docker access:** move container removal on delete into the worker (via the queue), so the API needs no Docker access.
- **Redis password:** add `--requirepass` as a second layer behind #1.
