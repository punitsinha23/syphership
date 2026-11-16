"""Structured (JSON) logs for the API and the worker.

Every log line is one JSON object, so it can be searched and filtered
("all lines for deployment 42"). Two IDs travel with the work:

- request_id: set per HTTP request (or taken from an X-Request-ID header), and
  passed to the worker inside the job, so one deploy can be followed from the
  click through the build.
- deployment_id: set while the worker handles a deployment.

Both live in contextvars, so every log call in that request or job picks them
up without passing them around. LOG_FORMAT=text gives readable lines locally."""

import json
import logging
import os
import sys
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
deployment_id_var: ContextVar[int | None] = ContextVar("deployment_id", default=None)

# Attributes every LogRecord has; anything else was passed with extra={...}.
# color_message: uvicorn's copy of the message with terminal colour codes.
_STANDARD_ATTRS = set(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {
    "message",
    "asctime",
    "taskName",
    "color_message",
}


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = request_id_var.get()
        if request_id:
            entry["request_id"] = request_id
        deployment_id = deployment_id_var.get()
        if deployment_id is not None:
            entry["deployment_id"] = deployment_id

        # Fields passed with logger.info("...", extra={"status": 200, ...})
        for key, value in vars(record).items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                entry[key] = value

        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(entry, default=str)


class TextFormatter(logging.Formatter):
    """Readable lines for local development, with the IDs when set."""

    def __init__(self):
        super().__init__("%(asctime)s %(levelname)s %(name)s: %(message)s")

    def format(self, record: logging.LogRecord) -> str:
        line = super().format(record)
        ids = []
        if request_id_var.get():
            ids.append(f"request_id={request_id_var.get()}")
        if deployment_id_var.get() is not None:
            ids.append(f"deployment_id={deployment_id_var.get()}")
        return f"{line} [{' '.join(ids)}]" if ids else line


def setup_logging() -> None:
    """Send all logs (ours, uvicorn's, libraries') through one formatter."""
    handler = logging.StreamHandler(sys.stdout)
    use_text = os.getenv("LOG_FORMAT", "json").lower() == "text"
    handler.setFormatter(TextFormatter() if use_text else JsonFormatter())

    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

    # Uvicorn installs its own handlers; route its logs through ours instead.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
    # Every request is logged by our middleware, with more detail.
    logging.getLogger("uvicorn.access").disabled = True
    # httpx logs every outgoing call at INFO (e.g. each Caddy reload); too noisy.
    logging.getLogger("httpx").setLevel(logging.WARNING)
