# Syphership Architecture

How the pieces fit, what happens during a deployment, and how the system behaves when things fail. For the threat model and sandboxing, see [SECURITY.md](SECURITY.md).

## 1. Components

```text
                       ┌──────────── one VPS (1 vCPU, 1 GB RAM + 2 GB swap) ────────────┐
                       │                                                                 │
 Browser ──HTTPS─────► │ Caddy :443 ─┬─ syphership.duckdns.org     → /var/www (React build)│
                       │             ├─ api.syphership.duckdns.org → API 127.0.0.1:8000   │
                       │             └─ <name>-<id>.syphership...  → app 127.0.0.1:<port> │
                       │                                                                 │
 GitHub ──webhook────► │ API (FastAPI) ──► PostgreSQL     (users, projects, deployments) │
                       │      │                                                          │
                       │      └─ job ──► Redis ──► Worker(s) ──► Docker daemon           │
                       │                 (queue, live logs,   (clone, build, run,        │
                       │                  rate limits,         health check,             │
                       │                  build metrics)       Caddy routes)             │
                       └─────────────────────────────────────────────────────────────────┘
```

| Component | Responsibility | Why it's separate |
|---|---|---|
| **API** (`services/api`, FastAPI) | Auth, projects, deployments, webhooks, live log stream, wake page, `/metrics` | Stateless and **never touches Docker**, so an API bug can't become root on the host. A test enforces that it never imports Docker code. |
| **Worker** (`services/api/worker`) | Builds and runs apps, writes Caddy routes, puts idle apps to sleep, cleans up | The only process with the Docker socket. Scales horizontally: more workers, more builds at once. |
| **PostgreSQL** | Source of truth: users, OAuth accounts, refresh tokens, projects, deployments | Everything else can be rebuilt from it. Backed up daily. |
| **Redis** | Job queue (Streams + consumer group), live build logs, rate limits, webhook dedupe, build metrics | Fast, short-lived data. Losing it loses no user data. |
| **Caddy** | HTTPS (Let's Encrypt) for the site, API and every app; routes app hostnames to containers | Apps and the API listen on 127.0.0.1 only; Caddy is the only public entry point. |

The API and worker share one codebase and one Docker image (`worker/Dockerfile`) and differ only in their start command. Everything runs from one `compose.yaml` using profiles: `prod` adds the API container, `workers` adds the worker.

## 2. A deployment, step by step

1. **Trigger.** The user clicks *Deploy*, or GitHub sends a push webhook. The webhook is checked with **HMAC-SHA256** against the project's own secret, and its delivery ID is remembered in Redis so a redelivered webhook doesn't deploy twice.
2. **Queue.** The API checks the user's app limit, inserts a `QUEUED` deployment, and `XADD`s a job (`deployment_id`, plus the `request_id` for logging) to the `deployments` stream. A unique partial index allows only one in-progress deployment per project.
3. **Claim.** A worker reads the job (`XREADGROUP`) and claims it with one conditional `UPDATE … WHERE status = 'QUEUED'`. If two workers get the same job, only one update succeeds; the other skips it.
4. **Clone.** The exact commit is cloned with the owner's GitHub token, passed through git's environment, never the URL, so it can't leak into logs.
5. **Build.** `docker build` runs with a 10-minute timer. Each output line is scrubbed of secrets and appended to the Redis Stream `logs:<id>` as it's printed. The full log is saved to PostgreSQL. The image is refused if it's over the size limit or would run as root.
6. **Run.** `docker run` with `--cap-drop ALL`, `no-new-privileges`, CPU/memory/PID limits, the separate `syphership-apps` network, and the port published on `127.0.0.1` only.
7. **Health check.** The worker polls the app for up to 60 seconds; if it never answers, the deployment fails with a message saying so.
8. **Go live.** Status becomes `RUNNING`, the app's Caddy route is rewritten to the new container, and **only then** are older deployments of the project stopped and removed, so the URL keeps working during a redeploy.
9. **Ack.** The worker `XACK`s the job.

## 3. Deployment state machine

```text
 QUEUED ──► BUILDING ──► DEPLOYING ──► RUNNING ◄──────────────┐
   │           │             │           │  │                 │
   └───────────┴─────────────┴──► FAILED ◄┘  │ idle 24 h       │ docker start
                                             v                 │ + health check
                                          SLEEPING ──visit──► WAKING
                                             │                 │
 RUNNING / SLEEPING / WAKING ──newer deployment goes live──► STOPPED
```

Allowed transitions live in one table (`ALLOWED_TRANSITIONS` in `deployment_services.py`), and a test checks that every status has an entry. Every change from a shared state uses a conditional `UPDATE … WHERE status = <expected>`, so a duplicate job, a second worker, or a redeploy racing a wake-up can never move a deployment backwards.

| Status | Container | Meaning |
|---|---|---|
| `QUEUED`, `BUILDING`, `DEPLOYING` | being made | In progress; at most one per project |
| `RUNNING` | running | Live at its URL |
| `SLEEPING` | stopped, kept | Idle; starts again on the next visit |
| `WAKING` | starting | A visitor arrived; the worker is starting it |
| `STOPPED` | removed | Replaced by a newer deployment |
| `FAILED` | removed | `failure_reason` and `failed_stage` say why and where |

## 4. The job queue (Redis Streams)

- **At-least-once delivery.** A job stays *pending* in the consumer group until the worker `XACK`s it after finishing. If a worker dies mid-job, another worker takes the job over with `XAUTOCLAIM` once it has been idle for 15 minutes (longer than the slowest build).
- **Idempotent handlers.** Delivery can happen twice, so every handler is safe to run twice: claiming is a conditional update, cleanup is "remove if it exists", and wake skips anything that isn't `WAKING`.
- **Dead letters.** A job delivered 3 times without finishing (it probably crashes the worker) is copied to `deployments:dead`, acked, and its deployment is marked `FAILED`. A malformed job goes straight there.
- **Job types.** Builds (`deployment_id`), cleanups (`action=cleanup`, when a deployment, project or account is deleted, since the API can't touch Docker) and wake-ups (`action=wake`).
- **Graceful shutdown.** On `SIGTERM` the worker finishes its current job before exiting (Compose gives it 15 minutes).

## 5. Routing and HTTPS

The worker owns `/etc/caddy/apps/apps.caddy`. On every change it **rebuilds the file from the database** (the newest `RUNNING`/`SLEEPING`/`WAKING` deployment per project), compares it with the current file, and only if it changed, writes it atomically and asks Caddy to reload through its admin API on `localhost:2019`. If the reload fails, the old file is put back and the next minute's check retries. Because the file is always derived from the database, a missed update fixes itself.

- A **running** app's block proxies to `127.0.0.1:<port>`.
- A **sleeping** app's block rewrites every request to the API's wake page.
- Every app block writes an access log to `/var/log/caddy/apps/<host>.log`, which is how idle sleep knows when the app was last used.

Caddy gets a Let's Encrypt certificate for each new hostname automatically. DuckDNS resolves every subdomain of `syphership.duckdns.org` to the server.

## 6. Idle sleep

Once a minute, one worker (chosen with a Redis `SET NX` lock that expires after 60 s) runs the periodic checks:

1. **Dead apps:** `RUNNING` deployments whose container has exited become `FAILED`.
2. **Activity:** each running app's last visit is the modification time of its Caddy access log; that moves `last_active_at` forward. The worker only checks a timestamp, it never parses the log.
3. **Sleep:** apps idle for `IDLE_SLEEP_HOURS` (24) are claimed `RUNNING → SLEEPING`, their route is switched to the wake page, then `docker stop` frees their memory. `docker pause` would keep it. If the stop fails, the app is put back to `RUNNING`.
4. **Routes** are synced (section 5).

**Waking:** the first request to a sleeping app hits the API's wake page, which moves `SLEEPING → WAKING` with a conditional update (so only one visitor queues the job) and returns a "Waking up…" page that refreshes every 3 seconds. The worker runs `docker start`, reads the app's **new** host port (Docker may pick a different one), health-checks it, marks it `RUNNING` and switches the route back. In production this takes about 3 seconds.

## 7. Live build logs

```text
docker build ─line─► worker ─XADD─► Redis Stream logs:<id> ─XREAD─► API ─SSE─► browser
```

- **Streams, not Pub/Sub,** so someone who opens the page mid-build still gets the earlier lines, and a reconnecting client resumes with `Last-Event-ID` (the stream entry ID).
- The stream is capped at about 5,000 lines and expires an hour after its last line. An `end` entry tells readers the build is over. The full log is stored in PostgreSQL either way.
- The browser reads the stream with `fetch` rather than `EventSource`, because `EventSource` can't send the `Authorization` header. Lines are added to the page in batches, 5 times a second.
- Publishing never raises: if Redis has a problem, the build still finishes; only the live view is lost.

## 8. Observability

- **Structured logs.** Every log line from the API and worker is one JSON object. Each API request gets an `X-Request-ID` (or keeps a valid one from the caller), and that ID **travels inside the job** to the worker, so one `grep` follows a deploy from the click to the end of the build. Worker lines also carry `deployment_id`.
- **`GET /metrics`** (Prometheus format, bearer token in production): request count and latency per route template, deployments by status, queue length and pending jobs, build duration histogram and outcomes. Builds happen in the worker but `/metrics` is served by the API, so the worker adds build numbers to counters in Redis and the API reads them; this also adds up correctly across several workers.
- **`/health`** (process up) and **`/ready`** (PostgreSQL and Redis reachable).

## 9. CI/CD and operations

```text
git push main ─► backend: ruff + pytest (real PostgreSQL + Redis)  ─┐
              └► frontend: eslint + vite build                      ├─► deploy (main only)
                                                                    ┘
deploy: build frontend ─► SSH (own key, pinned host key) ─► scripts/deploy.sh <sha>
        ─► rsync dist/ ─► curl the live site
```

`scripts/deploy.sh` checks out the **exact commit that passed CI** (`git reset --hard <sha>`, so the server always matches the repo), builds the image, runs `alembic upgrade head` **before** restarting, then waits for `/ready` and fails the job if it never comes. `concurrency: production` stops two deploys from overlapping.

**Backups:** `scripts/backup.sh` runs `pg_dump --format=custom` inside the PostgreSQL container from cron at 03:30 UTC and keeps 7 days. A restore into a throwaway database has been tested on production.

## 10. Failure handling

| What fails | What happens |
|---|---|
| Worker crashes mid-build | The job stays pending; another worker reclaims it and marks the deployment `FAILED` with a clear reason. The live log stream still expires. |
| A job keeps crashing workers | After 3 deliveries it goes to `deployments:dead` and its deployment fails. |
| App exits after going live | The per-minute check marks it `FAILED` and removes its route. |
| App never answers its health check | Fails after 60 s with a message to listen on `0.0.0.0`. |
| Build hangs | The 10-minute timer kills `docker build`. |
| Caddy reload fails | The old routes file is restored; the next sync retries. |
| Redis down | The API can't queue deployments and returns 503 (no half-created deployment is left `QUEUED`); `/ready` reports it. Builds already running still finish. |
| A webhook is delivered twice | The delivery ID was already seen; nothing happens. |
| A redeploy and a wake-up race | Conditional updates: whichever loses sees the status changed and leaves the deployment alone. |

## 11. Scaling, and where it stops

- **Bursts** are absorbed by the queue; more `worker` replicas build in parallel (`docker compose --profile workers up --scale worker=N`).
- **The API is stateless:** sessions are JWTs, and shared state lives in PostgreSQL and Redis.
- **Fairness:** per-user app limits and Redis rate limits on deploys, webhooks and auth endpoints.
- **The real bottleneck is the single Docker host:** builds and apps share 1 vCPU and 1 GB RAM, and idle sleep is what lets several apps fit. The next steps would be pushing images to a registry so building and running can happen on different machines, then an orchestrator (Kubernetes) for running apps. Those are in PROJECT.md's backlog.
- **Isolation limit:** containers share the host kernel. Hardening (non-root, no capabilities, limits, separate network) reduces the risk, but gVisor or VMs would be needed for truly hostile code; see SECURITY.md.
