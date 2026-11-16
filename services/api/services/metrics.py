"""Prometheus metrics, served by the API at GET /metrics.

Three kinds of numbers, from three places:

- HTTP requests and their latency: counted in the API process itself.
- Deployments by status and the job queue: read from Postgres and Redis at
  the moment Prometheus asks, so they're always current.
- Build durations and outcomes: builds run in the worker, a different
  process, so the worker adds them to counters in Redis (record_build) and
  the API reads those back. That also adds up correctly across several
  workers and survives restarts."""

import logging

import redis
from prometheus_client import Counter, Histogram
from prometheus_client.core import REGISTRY, CounterMetricFamily, GaugeMetricFamily, HistogramMetricFamily
from prometheus_client.registry import Collector
from sqlalchemy import func

from database import SessionLocal
from models.deployment import Deployment, DeploymentStatus
from services.queue import GROUP, STREAM, redis_client

logger = logging.getLogger(__name__)

# ---------- HTTP (in the API process) ----------

HTTP_REQUESTS = Counter(
    "syphership_http_requests_total",
    "HTTP requests handled by the API.",
    ["method", "route", "status"],
)
HTTP_LATENCY = Histogram(
    "syphership_http_request_duration_seconds",
    "Time to handle an HTTP request.",
    ["method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

# ---------- builds (written by the worker, read by the API) ----------

BUILD_STATS_KEY = "metrics:builds"
# Upper bounds in seconds; builds time out at 600.
BUILD_BUCKETS = (10, 30, 60, 120, 300, 600)


def record_build(seconds: float, succeeded: bool) -> None:
    """Called by the worker after each docker build. Never raises."""
    try:
        pipe = redis_client.pipeline()
        for bound in BUILD_BUCKETS:
            if seconds <= bound:
                pipe.hincrby(BUILD_STATS_KEY, f"le_{bound}", 1)
        pipe.hincrby(BUILD_STATS_KEY, "count", 1)
        pipe.hincrbyfloat(BUILD_STATS_KEY, "sum", seconds)
        pipe.hincrby(BUILD_STATS_KEY, "succeeded" if succeeded else "failed", 1)
        pipe.execute()
    except redis.exceptions.RedisError:
        logger.warning("Could not record build metrics.")


class SyphershipCollector(Collector):
    """Numbers read from Postgres and Redis each time /metrics is scraped."""

    def collect(self):
        yield from self._deployments()
        yield from self._queue_and_builds()

    def _deployments(self):
        gauge = GaugeMetricFamily(
            "syphership_deployments", "Deployments in each status.", labels=["status"]
        )
        try:
            db = SessionLocal()
            try:
                counts = dict(db.query(Deployment.status, func.count()).group_by(Deployment.status).all())
            finally:
                db.close()
        except Exception:
            logger.warning("Could not count deployments for metrics.")
            return
        for status in DeploymentStatus:
            gauge.add_metric([status.value], counts.get(status, 0))
        yield gauge

    def _queue_and_builds(self):
        try:
            length = redis_client.xlen(STREAM)  # 0 if the stream doesn't exist yet
            stats = redis_client.hgetall(BUILD_STATS_KEY)
        except redis.exceptions.RedisError:
            logger.warning("Could not read the queue for metrics.")
            return

        try:
            pending = redis_client.xpending(STREAM, GROUP)["pending"]
        except redis.exceptions.ResponseError:
            # No consumer group until the first worker starts: nothing pending.
            pending = 0
        except redis.exceptions.RedisError:
            logger.warning("Could not read pending jobs for metrics.")
            return

        yield GaugeMetricFamily("syphership_queue_length", "Jobs in the deployment stream.", value=length)
        yield GaugeMetricFamily(
            "syphership_queue_pending", "Jobs handed to a worker and not yet finished.", value=pending
        )

        outcomes = CounterMetricFamily(
            "syphership_builds", "Finished docker builds by outcome.", labels=["outcome"]
        )
        for outcome in ("succeeded", "failed"):
            outcomes.add_metric([outcome], int(stats.get(outcome, 0)))
        yield outcomes

        count = int(stats.get("count", 0))
        buckets = [(str(bound), int(stats.get(f"le_{bound}", 0))) for bound in BUILD_BUCKETS]
        buckets.append(("+Inf", count))
        yield HistogramMetricFamily(
            "syphership_build_duration_seconds",
            "Time docker build took.",
            buckets=buckets,
            sum_value=float(stats.get("sum", 0)),
        )


REGISTRY.register(SyphershipCollector())
