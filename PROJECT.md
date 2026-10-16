# Syphership — Project Development Plan

> **Tagline:** From code to production.
>
> **Project type:** Developer Deployment Platform / Mini PaaS
>
> **Primary goal:** Build a platform where a developer connects a GitHub repository, clicks **Deploy**, and Syphership automatically builds, containerizes, deploys, and exposes the application through a live URL.
>
> **Learning goal:** Use the project to understand full-stack development, backend architecture, microservices, asynchronous communication, Docker, Kubernetes, cloud infrastructure, and system design by actually building each part.

---

## 1. Product Vision

Syphership is a small Platform-as-a-Service (PaaS).

A developer should eventually be able to:

1. Sign in with GitHub.
2. Connect/select a GitHub repository.
3. Select a branch.
4. Create a project.
5. Click **Deploy**.
6. Syphership clones the repository.
7. A build worker creates a Docker image.
8. The image is stored in a container registry.
9. A deployment worker deploys it to Kubernetes.
10. Syphership monitors the deployment.
11. The developer receives a live URL.
12. Future pushes can automatically trigger deployments through GitHub webhooks.

Example:

```text
GitHub Repository
       |
       v
   Syphership
       |
       v
      Build
       |
       v
   Docker Image
       |
       v
  Container Registry
       |
       v
   Kubernetes
       |
       v
  Live Application
```

---

# 2. Core Engineering Principles

These rules guide the entire project.

- Do not add technology just to put it on the resume.
- Every service must have a clear responsibility.
- Every infrastructure component must solve an actual problem.
- Understand each technology before depending on it.
- Start simple and increase complexity deliberately.
- Prefer observable systems over hidden magic.
- Design for failure, not only the happy path.
- Document architectural decisions.
- Keep local development possible on an 8 GB RAM laptop.
- Build the MVP before adding production-scale infrastructure.

---

# 3. Target Architecture

The final learning architecture is approximately:

```text
                         ┌─────────────┐
                         │   GitHub    │
                         └──────┬──────┘
                                │
                                v
                         ┌─────────────┐
                         │   Next.js   │
                         │  Frontend   │
                         └──────┬──────┘
                                │
                                v
                         ┌─────────────┐
                         │ API Gateway │
                         └──────┬──────┘
                                │
             ┌──────────────────┼──────────────────┐
             v                  v                  v
      ┌─────────────┐   ┌─────────────┐   ┌──────────────┐
      │Auth Service │   │Project      │   │ Deployment   │
      │             │   │Service      │   │ Service      │
      └─────────────┘   └─────────────┘   └──────┬───────┘
                                                  │
                                                  v
                                           ┌─────────────┐
                                           │ Message Bus  │
                                           │ Redis/Kafka  │
                                           └──────┬──────┘
                                                  │
                              ┌───────────────────┼───────────────────┐
                              v                   v                   v
                       ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
                       │Build Worker │    │Deploy Worker│    │Notification │
                       │             │    │             │    │Service      │
                       └──────┬──────┘    └──────┬──────┘    └─────────────┘
                              │                  │
                              v                  v
                           Docker           Kubernetes
                              │                  │
                              v                  v
                      Container Registry    Live Pods
```

**Important:** We will NOT build this entire architecture immediately.

We will evolve toward it.

---

# 4. Technology Stack

## Frontend

- Next.js
- TypeScript
- Tailwind CSS
- React

## Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic

## Database

- PostgreSQL

## Caching / Initial Queue

- Redis

## Message Streaming — Later

- Apache Kafka

## Containers

- Docker
- Docker Compose

## Orchestration

- Kubernetes
- Initially: kind or k3d
- Later: cloud Kubernetes such as AWS EKS

## Source Control Integration

- GitHub OAuth
- GitHub REST API
- GitHub Webhooks

## Cloud — Later

Potential AWS components:

- EKS
- ECR
- RDS
- S3
- ElastiCache
- Route 53

## Observability — Later

- Prometheus
- Grafana
- OpenTelemetry

---

# 5. Development Phases

## Phase 0 — Project Foundation

**Goal:** Create a clean development environment.

- [ ] Create GitHub repository
- [ ] Create project directory
- [ ] Create `PROJECT.md`
- [ ] Define repository structure
- [ ] Initialize Git
- [ ] Create `.gitignore`
- [ ] Create `.env.example`
- [ ] Add basic documentation
- [ ] Create frontend project
- [ ] Create FastAPI backend
- [ ] Create Docker configuration
- [ ] Create local PostgreSQL setup
- [ ] Create local Redis setup
- [ ] Verify all services start

---

# 6. Phase 1 — MVP Backend

**Goal:** Build the core API before introducing microservices.

### Authentication

- [ ] User model
- [ ] Registration
- [ ] Login
- [ ] Password hashing
- [ ] JWT authentication
- [ ] Authentication dependency
- [ ] Protected endpoints

### Projects

- [ ] Create project
- [ ] List projects
- [ ] Get project
- [ ] Update project
- [ ] Delete project

### Deployments

Create deployment states:

```text
QUEUED
   ↓
BUILDING
   ↓
DEPLOYING
   ↓
RUNNING
```

Failure path:

```text
QUEUED → BUILDING → FAILED
QUEUED → BUILDING → DEPLOYING → FAILED
```

Tasks:

- [ ] Deployment model
- [ ] Create deployment endpoint
- [ ] Deployment status
- [ ] Deployment history
- [ ] Commit SHA tracking
- [ ] Deployment timestamps
- [ ] Failure reason storage

---

# 7. Phase 2 — Frontend MVP

**Goal:** Give the platform a usable dashboard.

Pages:

```text
/login
/register
/dashboard
/projects
/projects/[id]
/projects/[id]/deployments
/settings
```

Tasks:

- [ ] Authentication UI
- [ ] Dashboard
- [ ] Project creation
- [ ] Project details
- [ ] Deploy button
- [ ] Deployment status
- [ ] Deployment history
- [ ] Build logs UI
- [ ] Error states
- [ ] Loading states
- [ ] Responsive design

---

# 8. Phase 3 — GitHub Integration

**Goal:** Connect real repositories.

- [ ] GitHub OAuth
- [ ] Store GitHub account information
- [ ] Request required GitHub permissions
- [ ] List repositories
- [ ] Select repository
- [ ] Select branch
- [ ] Retrieve repository metadata
- [ ] Store repository configuration
- [ ] Test repository access

Target flow:

```text
User
 ↓
Login with GitHub
 ↓
Authorize Syphership
 ↓
Select Repository
 ↓
Select Branch
 ↓
Create Project
```

---

# 9. Phase 4 — First Real Deployment

**This is the first major milestone.**

**Goal:**

> A user can connect a GitHub repository and receive a live deployed application.

Architecture:

```text
Next.js
   ↓
FastAPI
   ↓
Deployment Request
   ↓
Build Worker
   ↓
git clone
   ↓
docker build
   ↓
docker run
```

Initially, we can deploy locally without Kubernetes.

Tasks:

- [x] Create deployment job
- [x] Clone GitHub repository
- [x] Detect/build application (build only: a root Dockerfile is required; auto-detection deferred)
- [x] Create Docker image
- [x] Start container
- [x] Assign port
- [x] Verify health
- [x] Store deployment URL
- [x] Capture build logs
- [x] Handle build failures

---

# 10. Phase 5 — Redis Queue + Workers

**Goal:** Learn asynchronous processing.

Instead of:

```text
API → Build
```

we introduce:

```text
API
 ↓
Redis Queue
 ↓
Build Worker
```

Concepts to learn:

- Producer
- Consumer
- Queue
- Job
- Worker
- Retry
- Timeout
- Failure
- Idempotency

Tasks:

- [ ] Create deployment queue
- [ ] Create worker process
- [ ] Publish deployment jobs
- [ ] Consume deployment jobs
- [ ] Update deployment state
- [ ] Store worker logs
- [ ] Implement retry
- [ ] Handle failed jobs
- [ ] Prevent duplicate jobs

---

# 11. Phase 6 — Docker Registry

**Goal:** Separate image building from image deployment.

Flow:

```text
GitHub
 ↓
Build Worker
 ↓
docker build
 ↓
Docker Image
 ↓
Container Registry
 ↓
Deploy Worker
```

Tasks:

- [ ] Choose registry
- [ ] Tag images
- [ ] Push images
- [ ] Store image reference
- [ ] Pull image during deployment
- [ ] Handle image build failure
- [ ] Handle registry failure

Local development may use a local registry.

---

# 12. Phase 7 — Kubernetes

**Goal:** Replace manually managed containers with Kubernetes.

Start locally.

Recommended options:

- kind
- k3d
- Minikube

For this project, keep the local Kubernetes environment lightweight.

Architecture:

```text
Deploy Worker
      ↓
Kubernetes API
      ↓
Deployment
      ↓
ReplicaSet
      ↓
Pods
      ↓
Container
```

Tasks:

- [ ] Learn Kubernetes fundamentals
- [ ] Create Deployment
- [ ] Create Service
- [ ] Create ConfigMap
- [ ] Create Secret
- [ ] Configure resource limits
- [ ] Configure readiness probe
- [ ] Configure liveness probe
- [ ] Deploy application programmatically
- [ ] Read pod status
- [ ] Detect failed deployment
- [ ] Implement basic rollback

---

# 13. Phase 8 — Live URLs and Ingress

**Goal:** Make deployed applications accessible through URLs.

Initial concept:

```text
myapp.syphership.local
```

Later:

```text
myapp.syphership.dev
```

Architecture:

```text
Internet
   ↓
DNS
   ↓
Ingress
   ↓
Kubernetes Service
   ↓
Pod
```

Tasks:

- [ ] Learn DNS basics
- [ ] Learn Kubernetes Ingress
- [ ] Configure Ingress Controller
- [ ] Route project subdomains
- [ ] Implement generated deployment URLs
- [ ] Configure HTTPS
- [ ] Learn TLS certificates
- [ ] Later support custom domains

---

# 14. Phase 9 — Microservices

**Important learning phase.**

We now deliberately split the system.

Initial services:

```text
Auth Service
Project Service
Deployment Service
Build Service
Deploy Service
Notification Service
```

Each service should have:

- [ ] Clear responsibility
- [ ] Separate FastAPI application
- [ ] Own configuration
- [ ] Health endpoint
- [ ] Logging
- [ ] Error handling
- [ ] Tests
- [ ] Dockerfile

---

# 15. Service Communication

We need to learn two major communication models.

## Synchronous Communication

Example:

```text
Project Service
      ↓ HTTP
Deployment Service
```

Use when an immediate response is required.

Learn:

- REST
- HTTP
- Timeouts
- Retries
- Service discovery
- Authentication between services

## Asynchronous Communication

Example:

```text
Deployment Service
       ↓
     Kafka
       ↓
   Build Service
```

Use when work can happen asynchronously.

Learn:

- Events
- Topics
- Producers
- Consumers
- Consumer groups
- Partitions
- Offsets
- Retries
- Dead-letter queues
- Event ordering
- Idempotency

---

# 16. Phase 10 — Kafka

**Goal:** Replace the simple Redis job queue with event-driven communication where appropriate.

Example:

```text
Deployment Service
       |
       | DeploymentCreated
       v
     Kafka
       |
       +------------------+
       |                  |
       v                  v
 Build Worker       Notification Service
       |
       | BuildCompleted
       v
     Kafka
       |
       v
 Deploy Worker
```

Potential topics:

```text
deployment.created
build.started
build.completed
build.failed
deployment.started
deployment.completed
deployment.failed
```

Tasks:

- [ ] Run Kafka locally
- [ ] Understand broker
- [ ] Create topics
- [ ] Create producer
- [ ] Create consumer
- [ ] Consumer groups
- [ ] Partitions
- [ ] Offsets
- [ ] Retries
- [ ] Dead-letter handling
- [ ] Idempotent consumers
- [ ] Event schemas

---

# 17. Phase 11 — GitHub Webhooks

**Goal:** Automatic deployments.

Target:

```text
Developer
   ↓
git push
   ↓
GitHub
   ↓
Webhook
   ↓
Syphership
   ↓
Deployment Event
   ↓
Build
   ↓
Deploy
```

Tasks:

- [ ] Create webhook endpoint
- [ ] Verify webhook signature
- [ ] Process push events
- [ ] Identify repository
- [ ] Identify branch
- [ ] Create deployment
- [ ] Publish event
- [ ] Build automatically
- [ ] Deploy automatically

---

# 18. Phase 12 — Deployment Logs

**Goal:** Give developers useful build/deployment visibility.

Example:

```text
$ git clone ...
✓ Repository cloned

$ docker build ...
✓ Installing dependencies
✓ Building application
✓ Image created

$ kubectl apply ...
✓ Deployment created
✓ Pod started
✓ Health check passed

Deployment successful.
URL: https://example.syphership.dev
```

Tasks:

- [ ] Capture worker logs
- [ ] Store logs
- [ ] Stream logs to frontend
- [ ] Add deployment log viewer
- [ ] Add timestamps
- [ ] Add log levels
- [ ] Handle large logs

---

# 19. Phase 13 — Observability

**Goal:** Understand what the distributed system is doing.

Implement:

- [ ] Structured logging
- [ ] Request IDs
- [ ] Deployment IDs
- [ ] Health checks
- [ ] Metrics
- [ ] Prometheus
- [ ] Grafana
- [ ] OpenTelemetry
- [ ] Distributed tracing

We should be able to trace:

```text
HTTP Request
 ↓
Deployment Service
 ↓
Kafka Event
 ↓
Build Worker
 ↓
Docker Build
 ↓
Kafka Event
 ↓
Deploy Worker
 ↓
Kubernetes
```

using a common correlation/trace ID.

---

# 20. Phase 14 — Reliability

**Goal:** Learn how distributed systems fail.

Implement and test:

- [ ] HTTP timeouts
- [ ] Retries
- [ ] Exponential backoff
- [ ] Circuit breaker concepts
- [ ] Idempotency
- [ ] Duplicate event handling
- [ ] Dead-letter queues
- [ ] Job timeouts
- [ ] Health checks
- [ ] Graceful shutdown
- [ ] Rollbacks

Failure scenarios to simulate:

```text
Build worker crashes
Kafka unavailable
PostgreSQL unavailable
Docker build fails
Image registry unavailable
Kubernetes pod crashes
Deployment never becomes healthy
Duplicate deployment event
Worker processes same job twice
```

---

# 21. Phase 15 — Security

Tasks:

- [ ] Secure password hashing
- [ ] JWT security
- [ ] GitHub OAuth security
- [ ] Webhook signature verification
- [ ] Environment variable management
- [ ] Secrets management
- [ ] API rate limiting
- [ ] Input validation
- [ ] Authorization
- [ ] Service-to-service authentication
- [ ] Container isolation
- [ ] Kubernetes security contexts
- [ ] Resource limits
- [ ] Prevent arbitrary host access
- [ ] Never expose secrets in logs

---

# 22. Phase 16 — Cloud Deployment

Only after the local architecture works.

Possible AWS architecture:

```text
                    Internet
                       |
                    Route 53
                       |
                  Load Balancer
                       |
                    Ingress
                       |
                      EKS
             ┌─────────┴─────────┐
             │                   │
          Services             Pods
             │
       ┌─────┼─────┐
       v     v     v
      RDS   Redis  Kafka
                    |
                   ECR
```

Potential AWS services:

- [ ] EKS
- [ ] ECR
- [ ] RDS PostgreSQL
- [ ] S3
- [ ] ElastiCache
- [ ] Route 53
- [ ] CloudWatch

**Cost rule:** Avoid expensive managed infrastructure until it is actually needed.

---

# 23. Phase 17 — Infrastructure as Code

Later:

- [ ] Terraform
- [ ] Kubernetes manifests
- [ ] Helm
- [ ] Environment-specific configuration
- [ ] Infrastructure documentation

Target:

```text
Terraform
   ↓
AWS Infrastructure
   ↓
EKS
   ↓
Syphership
```

---

# 24. Phase 18 — CI/CD

For Syphership itself:

```text
git push
   ↓
GitHub Actions
   ↓
Tests
   ↓
Build
   ↓
Docker Image
   ↓
Registry
   ↓
Deploy
```

Tasks:

- [ ] Linting
- [ ] Unit tests
- [ ] Integration tests
- [ ] Docker build
- [ ] Image publishing
- [ ] Deployment pipeline
- [ ] Environment variables/secrets
- [ ] Deployment rollback

---

# 25. Phase 19 — Advanced PaaS Features

Only after the core platform is reliable.

Possible features:

- [ ] Custom domains
- [ ] Automatic HTTPS
- [ ] Environment variables
- [ ] Secrets
- [ ] Deployment rollback
- [ ] Multiple replicas
- [ ] Horizontal Pod Autoscaling
- [ ] Resource limits
- [ ] Build caching
- [ ] Deployment previews
- [ ] Automatic redeployment
- [ ] Project deletion
- [ ] Build history
- [ ] Runtime logs
- [ ] Usage metrics
- [ ] Team/project permissions
- [ ] API keys

---

# 26. Database Model

Initial schema:

```text
users
├── id
├── email
├── password_hash
└── created_at

projects
├── id
├── user_id
├── name
├── github_repo
├── branch
└── created_at

deployments
├── id
├── project_id
├── status
├── commit_sha
├── docker_image
├── deployment_url
├── created_at
└── finished_at
```

Later tables may include:

```text
github_accounts
deployment_logs
environment_variables
domains
builds
service_instances
teams
api_keys
```

---

# 27. Initial API

## Authentication

```http
POST /auth/register
POST /auth/login
GET  /auth/me
```

## Projects

```http
GET    /projects
POST   /projects
GET    /projects/{id}
PATCH  /projects/{id}
DELETE /projects/{id}
```

## Deployments

```http
POST /projects/{id}/deploy
GET  /projects/{id}/deployments
GET  /deployments/{id}
GET  /deployments/{id}/logs
POST /deployments/{id}/rollback
```

## GitHub

```http
GET /github/repos
GET /github/repos/{owner}/{repo}
POST /github/webhook
```

---

# 28. Backend Structure — Initial

```text
backend/
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── auth.py
│   │   ├── projects.py
│   │   ├── deployments.py
│   │   └── github.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── project.py
│   │   └── deployment.py
│   │
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── project.py
│   │   └── deployment.py
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── github_service.py
│   │   └── deployment_service.py
│   │
│   ├── repositories/
│   │   ├── user_repository.py
│   │   ├── project_repository.py
│   │   └── deployment_repository.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── database.py
│   │
│   └── workers/
│       └── ...
│
├── migrations/
├── tests/
├── Dockerfile
├── requirements.txt
└── .env.example
```

Later, services will become independently deployable applications.

---

# 29. Frontend Structure

```text
frontend/
├── app/
│   ├── login/
│   ├── register/
│   ├── dashboard/
│   ├── projects/
│   │   └── [id]/
│   └── settings/
│
├── components/
│   ├── Navbar.tsx
│   ├── ProjectCard.tsx
│   ├── DeploymentStatus.tsx
│   ├── DeploymentHistory.tsx
│   ├── BuildLogs.tsx
│   └── DeployButton.tsx
│
├── lib/
│   └── api.ts
│
└── types/
```

---

# 30. Worker Structure

Eventually:

```text
workers/
├── build-worker/
├── deploy-worker/
└── notification-worker/
```

Each worker should be independently executable.

---

# 31. Local Development

The project should initially run locally.

Target:

```text
Next.js
FastAPI
PostgreSQL
Redis
Docker
Kubernetes
```

Use Docker Compose where practical.

Because development hardware is limited, avoid running unnecessary infrastructure simultaneously.

Kafka, Prometheus, Grafana, and Kubernetes should be introduced only when their learning objective becomes relevant.

---

# 32. Testing Strategy

## Unit Tests

Test:

- Authentication
- Services
- Business rules
- Deployment state transitions
- Event processing

## Integration Tests

Test:

```text
API → PostgreSQL
API → Redis
Service → Service
Worker → Queue
Worker → Docker
Worker → Kubernetes
```

## End-to-End Test

The most important E2E test:

```text
GitHub repository
       ↓
Create project
       ↓
Deploy
       ↓
Build
       ↓
Container
       ↓
Kubernetes
       ↓
Health check
       ↓
Live URL
```

---

# 33. Deployment State Machine

A deployment must have controlled state transitions.

```text
              ┌───────────┐
              │  QUEUED   │
              └─────┬─────┘
                    │
                    v
              ┌───────────┐
              │ BUILDING  │
              └─────┬─────┘
                ┌───┴───┐
                v       v
             FAILED  DEPLOYING
                        │
                        v
                    RUNNING
                        │
                     ┌──┴──┐
                     v     v
                  FAILED  STOPPED
```

Invalid state transitions should be rejected.

---

# 34. Key System Design Questions

Throughout development, we should be able to answer:

### Architecture

- Why FastAPI?
- Why separate services?
- When should a service communicate synchronously?
- When should it publish an event?

### Queues

- Why Redis initially?
- Why Kafka later?
- What happens if a worker crashes?
- How do we retry jobs?
- How do we avoid duplicate processing?

### Databases

- Which service owns which data?
- Should services share a database?
- When should we introduce separate databases?

### Kubernetes

- Why Kubernetes?
- What is a Pod?
- What is a Deployment?
- What is a Service?
- What is Ingress?
- How does Kubernetes restart failed containers?

### Scalability

- What happens when 1,000 users deploy simultaneously?
- How do we scale Build Workers?
- How do Kafka partitions help?
- What becomes the bottleneck?

### Reliability

- What happens if PostgreSQL goes down?
- What happens if Kafka goes down?
- What happens if a deployment gets stuck?
- How do we recover?

### Security

- Can one user's deployment access another user's deployment?
- How do we protect GitHub credentials?
- How do we isolate arbitrary user code?
- How do we prevent resource abuse?

---

# 35. Resume-Level Final Architecture

The final project should be capable of honestly demonstrating:

```text
Frontend
   │
Next.js + TypeScript
   │
   ▼
API Gateway
   │
   ├── Auth Service
   ├── Project Service
   └── Deployment Service
              │
              ▼
            Kafka
              │
       ┌──────┴──────┐
       ▼             ▼
 Build Workers   Deploy Workers
       │             │
     Docker      Kubernetes
       │             │
       ▼             ▼
      ECR           EKS
                     │
                     ▼
                 Live Apps
```

Supporting infrastructure:

```text
PostgreSQL
Redis
Kafka
Docker
Kubernetes
Prometheus
Grafana
OpenTelemetry
GitHub
AWS
Terraform
GitHub Actions
```

Only technologies actually implemented and understood should appear on the final resume.

---

# 36. MVP Definition

The MVP is **NOT**:

- Kafka
- AWS
- Terraform
- Prometheus
- Grafana
- Custom domains
- Autoscaling
- Multi-region deployment
- Payments
- Service mesh

The MVP is:

> **A user connects a GitHub repository, clicks Deploy, and Syphership builds and deploys the application and provides a working URL.**

Everything else supports the evolution of that capability.

---

# 37. Definition of Done

A feature is considered complete when:

- [ ] It works locally.
- [ ] The implementation is understood.
- [ ] Errors are handled.
- [ ] Relevant tests exist.
- [ ] Logs are available where appropriate.
- [ ] Configuration is documented.
- [ ] The architecture is documented.
- [ ] The feature can be explained in an interview.

---

# 38. Current Priority

We should NOT jump directly into microservices.

Our immediate sequence is:

```text
1. Project foundation
        ↓
2. FastAPI backend
        ↓
3. PostgreSQL
        ↓
4. Authentication
        ↓
5. Projects
        ↓
6. Deployments
        ↓
7. Next.js dashboard
        ↓
8. GitHub integration
        ↓
9. First local deployment
        ↓
10. Redis + Build Worker
        ↓
11. Docker Registry
        ↓
12. Kubernetes
        ↓
13. Microservices
        ↓
14. Kafka
        ↓
15. Cloud
```

---

# 39. Project Philosophy

Syphership is both a product and a learning project.

We are intentionally going to encounter the problems that distributed systems create.

The objective is not:

> "Use as many technologies as possible."

The objective is:

> **Build a real deployment platform and understand every layer well enough to design, debug, scale, and defend the architecture in an interview.**

---

## Current Status

**Project:** Syphership  
**Status:** Planning  
**Backend:** FastAPI  
**Frontend:** Next.js + TypeScript  
**Database:** PostgreSQL  
**Initial Queue:** Redis  
**Future Messaging:** Kafka  
**Containers:** Docker  
**Orchestration:** Kubernetes  
**Cloud:** AWS — later

### Current milestone

**Phase 0 — Project Foundation**

- [ ] Create repository
- [ ] Create directory structure
- [ ] Initialize backend
- [ ] Initialize frontend
- [ ] Configure PostgreSQL
- [ ] Configure Redis
- [ ] Configure Docker
- [ ] Run the complete local development environment

---

**Last updated:** 2026-09-12
