# Syphership — Project Development Plan

> **Tagline:** From code to production.
>
> **Project type:** Developer Deployment Platform / Mini PaaS
>
> **Primary goal:** A developer signs in with GitHub, picks a repository, clicks **Deploy**, and Syphership builds, containerizes, runs, and exposes the application at a live URL.
>
> **Learning goal:** Understand backend and frontend fundamentals end to end — API design, auth, databases, async workers, containers, security, and production operations — by building a real, secure, horizontally scalable platform.
>
> **Deadline:** 2026-10-31. The project is complete after **8 phases (0–7)**. Everything else lives in the post-launch backlog (Section 9).

---

## 1. Product Vision

A developer can:

1. Sign in with GitHub (or Google, then connect GitHub).
2. Select a GitHub repository and branch.
3. Create a project.
4. Click **Deploy** — or just `git push`.
5. Syphership queues the deployment.
6. A worker clones the repo and builds a Docker image from its `Dockerfile`.
7. The worker runs the container in a sandbox with resource limits.
8. Syphership health-checks it and routes `https://<project>.<domain>` to it.
9. The developer watches build logs live and sees the deployment history.

```text
GitHub Repo ──► Syphership API ──► Redis Queue ──► Build Worker(s)
                                                       │
                                               docker build / run
                                                       │
                                                       ▼
                                 Reverse Proxy (HTTPS) ──► Live App
```

---

## 2. Core Engineering Principles

- Do not add technology just to put it on the resume.
- Every component must solve a real problem in this system.
- Understand each technology before depending on it.
- Design for failure, not only the happy path.
- Secure by default: least privilege, no secrets in logs, untrusted user code is isolated.
- Scale by design: stateless API, work done by horizontally scalable workers.
- Keep local development possible on an 8 GB RAM laptop.
- **Ship by the deadline.** Each phase has *Must* and *Stretch* tasks. Stretch tasks are cut first.

---

## 3. Final Architecture (what we will actually ship)

```text
                         ┌──────────────┐
                         │    GitHub    │── push webhook ─┐
                         └──────┬───────┘                 │
                                │ OAuth / repo API        │
                                v                         v
 ┌──────────────┐        ┌──────────────────────────────────────┐
 │ React (Vite) │──────► │       FastAPI API (stateless)        │
 │  Dashboard   │  REST  │ auth · projects · deployments ·      │
 └──────────────┘  + SSE │ webhooks · rate limiting · metrics   │
                         └───────┬───────────────────┬──────────┘
                                 │                   │
                                 v                   v
                          ┌────────────┐     ┌────────────────┐
                          │ PostgreSQL │     │ Redis          │
                          │ (state)    │     │ queue (Stream) │
                          └────────────┘     │ rate limits    │
                                 ^           │ log pub/sub    │
                                 │           └───────┬────────┘
                                 │                   │ consumer group
                                 │       ┌───────────┼───────────┐
                                 │       v           v           v
                                 └─ Build Worker  Build Worker  ... (N)
                                         │
                                  docker build / run
                                  (sandboxed, isolated network)
                                         │
                                         v
                          ┌──────────────────────────────┐
                          │ Caddy reverse proxy (HTTPS)  │
                          │ <project>.<domain> ──► app   │
                          └──────────────────────────────┘
```

**Why this and not microservices + Kafka + Kubernetes?** One well-structured API plus a queue and N workers already demonstrates the key distributed-systems ideas (producers/consumers, consumer groups, at-least-once delivery, idempotency, retries, dead-letter queues, horizontal scaling) and can be finished, secured, and defended in an interview. Kafka, Kubernetes, and service splitting are documented as next steps (Section 9).

---

## 4. Technology Stack

| Area | Technology |
|---|---|
| Frontend | React 19, Vite, React Router, MUI |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Database | PostgreSQL |
| Queue / cache | Redis (Streams + consumer groups, rate limiting, pub/sub) |
| Auth | GitHub OAuth, Google OAuth, JWT access/refresh tokens |
| Source control | GitHub REST API, GitHub Webhooks |
| Containers | Docker, Docker Compose |
| Edge / HTTPS | Caddy (reverse proxy, automatic TLS) |
| CI | GitHub Actions |
| Hosting | A single Linux VPS / cloud VM running Docker Compose |
| Observability | Structured JSON logs, request IDs, Prometheus-format `/metrics` |

---

# 5. Development Phases

## Overview and Timeline

| Phase | Name | Status | Target dates |
|---|---|---|---|
| 0 | Project Foundation | ✅ Done | — |
| 1 | MVP Backend | ✅ Done | — |
| 2 | Frontend MVP | ✅ Done | — |
| 3 | GitHub Integration | ✅ Done | — |
| 4 | First Real Deployment | ✅ Done | — |
| 5 | Redis Queue + Scalable Workers | ✅ Done | Finished Nov 3 |
| 6 | Security Hardening + Push-to-Deploy | ✅ Done | Finished Nov 6 |
| 7 | Production Launch (URLs, HTTPS, logs, CI/CD, docs) | ✅ Done | Finished Nov 17 (live Nov 16) |

Rule: if a phase runs over its dates, cut its **Stretch** tasks — do not push the next phase.

---

## Phase 0 — Project Foundation ✅

- [x] Repository, directory structure, Git, `.gitignore`, `.env.example`
- [x] FastAPI backend and React frontend projects
- [x] Docker Compose with PostgreSQL and Redis
- [x] All services start locally

## Phase 1 — MVP Backend ✅

- [x] User model and auth dependency on protected endpoints
- [x] JWT access + refresh tokens
- [x] Project CRUD
- [x] Deployment model, state machine, history, commit SHA, timestamps, failure reason
- [x] Alembic migrations, indexes
- [x] Tests

> Auth was redesigned to **OAuth-only** (GitHub + Google) — no passwords stored, which removes password-reuse and unverified-email takeover risks.

## Phase 2 — Frontend MVP ✅

- [x] Login, OAuth callback, dashboard, projects, project details, deployment details, settings
- [x] Deploy button, status badges, deployment timeline, history, build logs view
- [x] Loading and error states, polling for status

## Phase 3 — GitHub Integration ✅

- [x] GitHub OAuth with signed `state` + cookie nonce, one-time login codes
- [x] Store linked accounts (`oauth_accounts`)
- [x] List repositories and branches, store repo configuration on the project

## Phase 4 — First Real Deployment ✅

- [x] Create deployment job (FastAPI `BackgroundTasks`)
- [x] Clone repo, `docker build` from root `Dockerfile` (auto-detection deliberately deferred)
- [x] Start container with resource limits, assign port, health check
- [x] Store URL and build logs, handle build failures
- [x] Mark interrupted deployments FAILED on startup

---

## Phase 5 — Redis Queue + Scalable Workers ✅

**Dates:** Oct 17 – Oct 21

**Goal:** Move builds out of the API process into separate, horizontally scalable worker processes, and make job processing reliable.

Today builds run inside the API process (`BackgroundTasks`): an API restart kills builds, and the API cannot scale independently of build load. After this phase:

```text
API ──XADD──► Redis Stream "deployments" ──XREADGROUP──► Worker 1
 (producer)        (consumer group "builders")      ├──► Worker 2
                                                    └──► Worker N
                         failed N times ──► "deployments:dead" (DLQ)
```

**Why Redis Streams (not a plain list or a library like RQ/Celery):** consumer groups, acknowledgements (`XACK`), pending-entry lists and `XAUTOCLAIM` teach the same concepts as Kafka (consumer groups, offsets/acks, at-least-once delivery, redelivery) using infrastructure we already run.

Concepts to learn: producer, consumer, consumer group, ack, at-least-once delivery, idempotency, retry with backoff, dead-letter queue, visibility timeout / stuck jobs, graceful shutdown, backpressure.

### Must

- [x] Fix leftover bugs first: naive vs aware timestamps, timeline on FAILED, remove stray `mui` package and stale `src/pages/DeploymentDetails.jsx`
- [x] `worker/` entrypoint (`python -m worker`) that reuses the existing `deployment_runner`
- [x] API publishes a job (`deployment_id` only) **after** the DB commit; `BackgroundTasks` removed
- [x] Worker consumes with `XREADGROUP`, `XACK`s only after the deployment reaches a final state
- [x] Idempotency: worker claims a job with a conditional update (`UPDATE ... SET status='BUILDING' WHERE id=? AND status='QUEUED'`); if 0 rows change, skip — duplicate deliveries are harmless
- [x] Dead-letter stream for jobs that exceed max attempts (`MAX_DELIVERIES`) or are malformed; deployment marked FAILED with a reason
- [x] Stuck-job recovery with `XAUTOCLAIM` (replaces the startup "mark interrupted as FAILED" cleanup); a job abandoned mid-build is failed cleanly, a job abandoned while QUEUED is built
- [x] Build timeout: `docker build` 10 min, plus per-step timeouts for run, inspect and health check
- [x] Graceful shutdown: on SIGTERM/SIGINT finish the current job, don't take new ones; `stop_grace_period: 15m` in compose
- [x] Worker as its own service in `compose.yaml` (profile `workers`); `docker compose --profile workers up --build --scale worker=2` processes two deployments in parallel
- [x] Redis persistence (`--appendonly yes` + volume) so queued jobs and acks survive a Redis restart
- [x] Tests: publish → consume → ack; duplicate claim is skipped; recovery paths; malformed and over-delivered jobs land in the DLQ
- Moved to backlog: retries for transient errors with exponential backoff (most failures are in the user's code and would fail again)

### Stretch

- [ ] Per-user concurrency limit (max 1–2 active builds per user) — fairness and abuse protection
- [ ] Queue depth exposed on an admin/health endpoint

**Done when:** killing a worker mid-build results in the job being picked up again (or failed cleanly), and two workers process jobs in parallel without ever running the same deployment twice.

---

## Phase 6 — Security Hardening + Push-to-Deploy ✅

**Dates:** Oct 22 – Oct 26

**Goal:** Make the platform safe to run untrusted user code on, and deploy automatically on `git push`.

A PaaS runs strangers' code on your machine. This phase is what makes the project "secure" rather than a demo. Write the threat model first (`docs/SECURITY.md`): assets (DB, tokens, host, other users' apps), attackers (malicious repo owner, other users, the internet), and the mitigation for each item below.

### Must — Untrusted code isolation

- [x] Deployed containers must run as non-root (root images are refused), with `--cap-drop=ALL`, `--security-opt=no-new-privileges`, `--pids-limit`, memory/CPU limits
- [x] Deployed apps run on a separate Docker network: they **cannot** reach PostgreSQL, Redis, the API, or the Docker socket
- [x] Only the worker has access to the Docker socket; the API never does (document why: socket = root on host)
- [x] Limits: max repo size, build timeout (Phase 5), max image size, max running apps per user

### Must — Secrets and data

- [x] Encrypt OAuth access tokens at rest (Fernet, key derived from `SECRET_KEY`)
- [x] Private repos: request repo scope (or GitHub App), clone with the token **without** it appearing in build logs, error messages, or `git remote -v`
- [x] Scrub secrets from build logs and API errors (test it)
- [x] Per-project environment variables, encrypted at rest, injected at `docker run`, shown masked in the UI

### Must — API security

- [x] Authorization tests: user A gets 404 on user B's projects, deployments, logs (IDOR)
- [x] Validate repo names, branch names, and commit SHAs before they reach `git`/`docker` (no shell injection; never `shell=True`)
- [x] Rate limiting with Redis (fixed window or token bucket) on auth, deploy, and webhook endpoints
- [x] Strict CORS origins, security headers, short-lived access tokens, refresh token rotation reviewed

### Must — Push-to-deploy (GitHub Webhooks)

```text
git push ──► GitHub ──► POST /github/webhook ──► verify HMAC ──► create deployment ──► queue
```

- [x] Webhook endpoint that verifies `X-Hub-Signature-256` (HMAC-SHA256, constant-time compare)
- [x] Deduplicate by `X-GitHub-Delivery` (stored in Redis with a TTL) — replay protection
- [x] Handle `push` events: match repo + branch to projects, create a deployment for the pushed commit
- [x] Register/unregister the webhook when a project is created/deleted (or document manual setup)
- [x] "Auto-deploy on push" toggle per project

### Stretch

- [ ] `pip-audit` / `npm audit` in CI (Phase 7)
- [ ] Read-only root filesystem for deployed containers where possible

**Done when:** `docs/SECURITY.md` exists, and a test repo whose app tries to connect to `postgres:5432` or call the Docker socket fails; a forged webhook is rejected; a push deploys automatically.

---

## Phase 7 — Production Launch

**Dates:** Oct 27 – Oct 31

**Goal:** Run Syphership on the internet with real URLs and HTTPS, live logs, basic observability, CI, and documentation good enough for a resume and interviews.

### Must — Container hardening (moved from Phase 6)

- [x] Refresh token rotation
- [x] Mark `RUNNING` deployments as failed when their container has died

### Must — Product pages and access

- [x] Docs page
- [x] Account settings, including delete account
- [x] Privacy and Terms pages (drafts; review before going public)
- [x] Invite-only sign-up (`ALLOWED_EMAILS`)

### Must — Live URLs + HTTPS

```text
Internet ──► DuckDNS (*.syphership.duckdns.org) ──► Caddy :443 ──► <name>-<id> container
```

- [x] Caddy reverse proxy in front of the API, frontend, and deployed apps
- [x] Each project gets `https://<name>-<project id>.syphership.duckdns.org`; the worker rebuilds Caddy's app routes from the database and reloads Caddy through its admin API
- [x] Automatic TLS (Let's Encrypt, one certificate per hostname; DuckDNS instead of a paid domain)
- [x] Deployed app ports are published on 127.0.0.1 only; Caddy is the only way in
- [x] *(added)* Idle apps sleep after 24 h (`docker stop`) and wake on the next visit (new `SLEEPING`/`WAKING` states)

### Must — Live build logs

- [x] Worker reads `docker build` line by line (`Popen`) and appends each line to a Redis **Stream** per deployment (Streams instead of pub/sub, so late visitors and reconnects get earlier lines); the full log is still stored in PostgreSQL
- [x] `GET /deployments/{id}/logs/stream` using Server-Sent Events, resumable with `Last-Event-ID`
- [x] Frontend streams live (fetch, since EventSource can't send the auth header), then shows the stored log; stream capped at ~5,000 lines

### Must — Observability

- [x] Structured JSON logs with `request_id` and `deployment_id` carried from API to worker (through the job payload)
- [x] `/health` (liveness) and `/ready` (DB + Redis reachable) endpoints
- [x] `/metrics` in Prometheus format: request count/latency, deployments by status, build duration, queue depth (bearer token in production)

### Must — CI/CD and hosting

- [x] GitHub Actions: lint (ruff, eslint), backend tests with Postgres + Redis service containers, frontend build
- [ ] Docker image build in CI *(the deploy job builds it on the server instead)*
- [x] Production setup: one `compose.yaml` with `prod` and `workers` profiles (instead of a separate `compose.prod.yaml`); frontend served by Caddy; secrets in an untracked `.env`
- [x] Deploy to a VPS (1 vCPU / 1 GB) automatically after CI passes on `main`; daily `pg_dump` backups with 7-day retention, restore tested
- [ ] One automated end-to-end test (create project → deploy sample repo → URL returns 200) *(done by hand)*

### Must — Documentation (the resume part)

- [x] `README.md`: what it is, screenshots, architecture diagram, how to run locally, live demo link
- [x] `docs/ARCHITECTURE.md`: components, deployment flow, state machine, queue semantics, scaling story
- [x] `docs/SECURITY.md` (from Phase 6)
- [ ] Short demo video
- [x] Resume bullets written (Section 13)

### Stretch

- [ ] Prometheus + Grafana dashboard (only if RAM allows) *(not on 1 GB)*
- [ ] Rollback: redeploy a previous successful image
- [x] Deploy-on-merge for Syphership itself from GitHub Actions

**Done when:** a stranger can open the live site, sign in, deploy a sample repo, and get a working HTTPS URL.

---

# 6. Deployment State Machine

```text
 QUEUED ──► BUILDING ──► DEPLOYING ──► RUNNING ◄──────────────┐
   │           │             │           │  │                 │
   └───────────┴─────────────┴──► FAILED ◄┘  │ idle 24 h       │ docker start
                                             v                 │ + health check
                                          SLEEPING ──visit──► WAKING
                                             │                 │
 RUNNING / SLEEPING / WAKING ──newer deployment goes live──► STOPPED
```

Invalid transitions are rejected (`ALLOWED_TRANSITIONS`). Every change from a shared state is a conditional `UPDATE … WHERE status = <expected>`, which is what makes duplicate job delivery and races (redeploy vs. wake-up) safe. Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

# 7. Database Model

```text
users            id, email, username, avatar_url, created_at
oauth_accounts   id, user_id, provider, provider_user_id, access_token (→ encrypted, Phase 6)
login_codes      code_hash, user_id, expires_at
projects         id, user_id, name, description, created_at,
                 repo_id, repo_full_name, repo_branch, repo_clone_url, repo_html_url, repo_private
deployments      id, project_id, status, commit_sha, container_id, host_port, url,
                 failure_reason, build_logs, created_at, updated_at
```

Added in Phases 5–7 (as built):

```text
deployments      + failed_stage, last_active_at; statuses STOPPED, SLEEPING, WAKING
projects         + webhook_id, webhook_secret (encrypted), auto_deploy,
                   env_vars (encrypted JSON)
refresh_tokens   jti, user_id, expires_at, used_at   (rotation + reuse detection)
```

---

# 8. API

```http
# Auth
GET  /github/login            GET /github/callback       POST /github/connect
GET  /google/login            GET /google/callback
POST /auth/exchange           POST /auth/refresh         GET  /auth/me

# GitHub
GET  /github/repos
GET  /github/repos/{owner}/{repo}/branches
POST /github/webhook/{project_id}            # Phase 6

# Projects
GET /projects   POST /projects   GET /projects/{id}   PUT /projects/{id}   DELETE /projects/{id}
GET/PUT/DELETE  /projects/{id}/env           # Phase 6

# Deployments
POST   /deployments
GET    /deployments
GET    /deployments/{id}
GET    /deployments/{id}/logs
GET    /deployments/{id}/logs/stream         # Phase 7 (SSE)
DELETE /deployments/{id}

# Operations
GET /health   GET /ready   GET /metrics      # Phase 7
```

---

# 9. Post-Launch Backlog (not part of the deadline)

Learned topics to pick up after launch, in a sensible order. Each one is a strong interview talking point *only once actually built*.

1. **Container registry** — push images to a registry (local `registry:2`, GHCR, or ECR) so build and run can happen on different machines.
2. **Kubernetes (k3d/kind)** — replace `docker run` with Deployments, Services, Ingress, readiness/liveness probes, HPA.
3. **Kafka** — replace Redis Streams with topics (`deployment.created`, `build.completed`, …) when multiple independent consumers need the same events.
4. **Split services** — separate build service and notification service once there is a real reason (independent scaling or ownership).
5. **Cloud + IaC** — Terraform for a cloud setup (EKS/ECR/RDS) — watch costs.
6. **PaaS features** — custom domains, preview deployments per PR, build caching, Dockerfile auto-detection/buildpacks, runtime logs, teams, API keys.
7. **Full observability** — OpenTelemetry tracing across API → queue → worker, Grafana dashboards.
8. **Job retries** — retry transient failures (Docker daemon, network, GitHub) with exponential backoff and a max attempt count; never retry errors in the user's code.

---

# 10. Testing Strategy

- **Unit:** auth, state transitions, webhook signature verification, log scrubbing, rate limiter, input validation.
- **Integration:** API ↔ PostgreSQL, API → Redis Stream → worker, worker → Docker (marked slow).
- **Security:** IDOR tests across users, forged webhook rejected, secrets absent from logs, deployed app cannot reach internal services.
- **End-to-end:** sample repo → project → deploy → build → run → health check → HTTPS URL returns 200.

---

# 11. Key System Design Questions (be ready to answer)

**Architecture**
- Why one API + workers instead of microservices? What would trigger a split?
- Why is the API stateless, and why does that matter for scaling?

**Queues**
- What happens if a worker crashes mid-build? (pending entries + `XAUTOCLAIM`)
- How do we avoid running a deployment twice? (at-least-once delivery + idempotent conditional claim)
- Which failures are retried and which are not? What is the DLQ for?
- When would Kafka be a better choice than Redis Streams?

**Scalability**
- What happens when 1,000 users click Deploy at once? (queue absorbs bursts, workers scale horizontally, per-user limits keep it fair)
- What is the bottleneck? (Docker build CPU/disk on the worker host → next step is a registry + multiple build hosts / Kubernetes)

**Reliability**
- What happens if PostgreSQL or Redis goes down?
- What happens if a deployment never becomes healthy?

**Security**
- Can one user's app reach another user's app, or our database? (separate network, no socket, dropped capabilities)
- How are GitHub tokens and env vars protected? (encrypted at rest, scrubbed from logs)
- How do we know a webhook really came from GitHub? (HMAC + delivery-ID dedupe)
- Why is the Docker socket dangerous, and who can access it?

---

# 12. Definition of Done

A feature is complete when:

- [ ] It works locally and in production.
- [ ] Errors are handled and logged with context.
- [ ] Relevant tests exist and pass in CI.
- [ ] Configuration is documented.
- [ ] It can be explained in an interview.

---

# 13. Resume Summary

**Syphership — self-hosted deployment platform (mini PaaS)** · [syphership.duckdns.org](https://syphership.duckdns.org)
*FastAPI, PostgreSQL, Redis Streams, Docker, React, Caddy, GitHub Actions*

- Built a PaaS that deploys any Dockerized GitHub repository to its own HTTPS subdomain on `git push`, using GitHub OAuth, HMAC-verified webhooks, and a worker that clones, builds, sandboxes and health-checks each app.
- Designed an at-least-once job pipeline on Redis Streams consumer groups with idempotent conditional-update claims, crash recovery (`XAUTOCLAIM`), a dead-letter queue, and graceful shutdown; workers scale horizontally.
- Sandboxed untrusted code (non-root, all capabilities dropped, CPU/memory/PID limits, isolated network, localhost-only ports behind Caddy) and encrypted OAuth tokens and app secrets at rest; added rotating refresh tokens with reuse detection and Redis rate limiting.
- Cut memory use on a 1 GB server by putting idle apps to sleep and waking them on the next request in ~3 s, with zero-downtime redeploys via database-driven Caddy routing.
- Streamed live build logs to the browser over Server-Sent Events backed by Redis Streams; added JSON logs with request IDs propagated from API to worker, and Prometheus metrics.
- Shipped with CI/CD on GitHub Actions (ruff, ~400 pytest tests against real PostgreSQL/Redis, eslint) that deploys the tested commit to a VPS over SSH, plus daily verified database backups.

Only list what is actually implemented and understood.

---

## Current Status

**Phase:** 7 — Production Launch ✅ (all phases 0–7 done)
**Live:** https://syphership.duckdns.org (open sign-ups since 2026-11-16)
**Left from Phase 7:** demo video; automated end-to-end test; Docker image build in CI
**Next:** post-launch backlog (Section 9)

---

**Last updated:** 2026-11-17
