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
| 5 | Redis Queue + Scalable Workers | ⏳ Next | Oct 17 – Oct 21 |
| 6 | Security Hardening + Push-to-Deploy | ⬜ | Oct 22 – Oct 26 |
| 7 | Production Launch (URLs, HTTPS, logs, CI/CD, docs) | ⬜ | Oct 27 – Oct 31 |

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

## Phase 5 — Redis Queue + Scalable Workers ⏳

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

- [ ] Fix leftover bugs first: naive vs aware timestamps, timeline on FAILED, remove stray `mui` package and stale `src/pages/DeploymentDetails.jsx`
- [ ] `worker/` entrypoint (`python -m worker`) that reuses the existing `deployment_runner`
- [ ] API publishes a job (`deployment_id` only) **after** the DB commit; `BackgroundTasks` removed
- [ ] Worker consumes with `XREADGROUP`, `XACK`s only after the deployment reaches a final state
- [ ] Idempotency: worker claims a job with a conditional update (`UPDATE ... SET status='BUILDING' WHERE id=? AND status='QUEUED'`); if 0 rows change, skip — duplicate deliveries are harmless
- [ ] Retries for transient errors (Docker daemon / network) with exponential backoff and a max attempt count; build errors in the user's code are **not** retried
- [ ] Dead-letter stream for jobs that exceed max attempts; deployment marked FAILED with a reason
- [ ] Stuck-job recovery with `XAUTOCLAIM` (replaces the startup "mark interrupted as FAILED" cleanup)
- [ ] Build timeout (e.g. 10 min) enforced by the worker
- [ ] Graceful shutdown: on SIGTERM finish or release the current job, don't take new ones
- [ ] Worker as its own service in `compose.yaml`; run `docker compose up --scale worker=2` and show two deployments building in parallel
- [ ] Tests: publish → consume → state change; duplicate job is skipped; failed job lands in DLQ

### Stretch

- [ ] Per-user concurrency limit (max 1–2 active builds per user) — fairness and abuse protection
- [ ] Queue depth exposed on an admin/health endpoint

**Done when:** killing a worker mid-build results in the job being picked up again (or failed cleanly), and two workers process jobs in parallel without ever running the same deployment twice.

---

## Phase 6 — Security Hardening + Push-to-Deploy

**Dates:** Oct 22 – Oct 26

**Goal:** Make the platform safe to run untrusted user code on, and deploy automatically on `git push`.

A PaaS runs strangers' code on your machine. This phase is what makes the project "secure" rather than a demo. Write the threat model first (`docs/SECURITY.md`): assets (DB, tokens, host, other users' apps), attackers (malicious repo owner, other users, the internet), and the mitigation for each item below.

### Must — Untrusted code isolation

- [ ] Deployed containers run as non-root, `--cap-drop=ALL`, `--security-opt=no-new-privileges`, `--pids-limit`, memory/CPU limits (already have limits)
- [ ] Deployed apps run on a separate Docker network: they **cannot** reach PostgreSQL, Redis, the API, or the Docker socket
- [ ] Only the worker has access to the Docker socket; the API never does (document why: socket = root on host)
- [ ] Limits: max repo size, build timeout (Phase 5), max image size, max running apps per user

### Must — Secrets and data

- [ ] Encrypt OAuth access tokens at rest (Fernet key from env); currently stored in plain text
- [ ] Private repos: request repo scope (or GitHub App), clone with the token **without** it appearing in build logs, error messages, or `git remote -v`
- [ ] Scrub secrets from build logs and API errors (test it)
- [ ] Per-project environment variables, encrypted at rest, injected at `docker run`, shown masked in the UI

### Must — API security

- [ ] Authorization tests: user A gets 404 on user B's projects, deployments, logs (IDOR)
- [ ] Validate repo names, branch names, and commit SHAs before they reach `git`/`docker` (no shell injection; never `shell=True`)
- [ ] Rate limiting with Redis (fixed window or token bucket) on auth, deploy, and webhook endpoints
- [ ] Strict CORS origins, security headers, short-lived access tokens, refresh token rotation reviewed

### Must — Push-to-deploy (GitHub Webhooks)

```text
git push ──► GitHub ──► POST /github/webhook ──► verify HMAC ──► create deployment ──► queue
```

- [ ] Webhook endpoint that verifies `X-Hub-Signature-256` (HMAC-SHA256, constant-time compare)
- [ ] Deduplicate by `X-GitHub-Delivery` (stored in Redis with a TTL) — replay protection
- [ ] Handle `push` events: match repo + branch to projects, create a deployment for the pushed commit
- [ ] Register/unregister the webhook when a project is created/deleted (or document manual setup)
- [ ] "Auto-deploy on push" toggle per project

### Stretch

- [ ] `pip-audit` / `npm audit` in CI (Phase 7)
- [ ] Read-only root filesystem for deployed containers where possible

**Done when:** `docs/SECURITY.md` exists, and a test repo whose app tries to connect to `postgres:5432` or call the Docker socket fails; a forged webhook is rejected; a push deploys automatically.

---

## Phase 7 — Production Launch

**Dates:** Oct 27 – Oct 31

**Goal:** Run Syphership on the internet with real URLs and HTTPS, live logs, basic observability, CI, and documentation good enough for a resume and interviews.

### Must — Live URLs + HTTPS

```text
Internet ──► DNS (*.apps.<domain>) ──► Caddy :443 ──► <project> container
```

- [ ] Caddy reverse proxy in front of the API, frontend, and deployed apps
- [ ] Each deployment gets `https://<project-slug>.apps.<domain>` instead of `localhost:<port>`; the worker updates the route on deploy (Caddy admin API or generated config)
- [ ] Automatic TLS (Let's Encrypt). Wildcard certs need a DNS challenge — alternatively use on-demand TLS or a free `sslip.io`/`nip.io` hostname
- [ ] Deployed app ports are no longer published on the host

### Must — Live build logs

- [ ] Worker publishes log lines to Redis pub/sub (and still stores the full log in PostgreSQL)
- [ ] `GET /deployments/{id}/logs/stream` using Server-Sent Events
- [ ] Frontend log viewer streams live, then falls back to stored logs; cap log size

### Must — Observability

- [ ] Structured JSON logs with `request_id` and `deployment_id` carried from API to worker (through the job payload)
- [ ] `/health` (liveness) and `/ready` (DB + Redis reachable) endpoints
- [ ] `/metrics` in Prometheus format: request count/latency, deployments by status, build duration, queue depth

### Must — CI/CD and hosting

- [ ] GitHub Actions: lint (ruff, eslint), backend tests with Postgres + Redis service containers, frontend build, Docker image build
- [ ] Production `compose.prod.yaml`: API, worker(s), frontend (static build served by Caddy), PostgreSQL, Redis, Caddy; secrets from env, not committed
- [ ] Deploy to a VPS / cloud VM; database backups (daily `pg_dump`)
- [ ] One end-to-end test: create project → deploy sample repo → URL returns 200

### Must — Documentation (the resume part)

- [ ] `README.md`: what it is, screenshot/GIF, architecture diagram, how to run locally, live demo link
- [ ] `docs/ARCHITECTURE.md`: components, deployment flow, state machine, queue semantics, scaling story
- [ ] `docs/SECURITY.md` (from Phase 6)
- [ ] Short demo video
- [ ] Resume bullets written (Section 13)

### Stretch

- [ ] Prometheus + Grafana dashboard (only if RAM allows)
- [ ] Rollback: redeploy a previous successful image
- [ ] Deploy-on-merge for Syphership itself from GitHub Actions

**Done when:** a stranger can open the live site, sign in, deploy a sample repo, and get a working HTTPS URL.

---

# 6. Deployment State Machine

```text
              ┌───────────┐
              │  QUEUED   │
              └─────┬─────┘
                    │ worker claims job (conditional UPDATE)
                    v
              ┌───────────┐
              │ BUILDING  │
              └─────┬─────┘
                ┌───┴───┐
                v       v
             FAILED  DEPLOYING
                        │
                    ┌───┴───┐
                    v       v
                 FAILED  RUNNING
                            │ newer deployment of same project
                            v
                         STOPPED
```

Invalid transitions are rejected. Workers only move a deployment forward from the state they claimed it in, which is what makes duplicate job delivery safe.

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

Added in Phases 5–7:

```text
deployments      + attempts, image_tag, started_at, finished_at
projects         + slug, auto_deploy
project_env_vars id, project_id, key, value_encrypted, created_at
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
POST /github/webhook                         # Phase 6

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

# 13. Resume Summary (target, true after Phase 7)

**Syphership — self-hosted deployment platform (mini PaaS)**
*FastAPI, PostgreSQL, Redis Streams, Docker, React, Caddy, GitHub Actions*

- Built a PaaS that deploys GitHub repositories to HTTPS subdomains on `git push`, using GitHub OAuth, HMAC-verified webhooks, and a Docker-based build pipeline.
- Designed an at-least-once job pipeline on Redis Streams consumer groups with idempotent workers, exponential-backoff retries, a dead-letter queue, and crash recovery; scaled builds horizontally across worker replicas.
- Sandboxed untrusted user code (non-root, dropped capabilities, resource limits, isolated network) and encrypted OAuth tokens and environment secrets at rest; added Redis rate limiting and cross-tenant authorization tests.
- Streamed live build logs to the dashboard via Server-Sent Events; added structured logs with request/deployment IDs, Prometheus metrics, and CI with GitHub Actions.

Only list what is actually implemented and understood.

---

## Current Status

**Phase:** 5 — Redis Queue + Scalable Workers (started 2026-10-17)
**Done:** Phases 0–4
**Next:** Phase 6 — Security Hardening + Push-to-Deploy (Oct 22)
**Launch target:** 2026-10-31

---

**Last updated:** 2026-10-17
