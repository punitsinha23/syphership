# Build worker. Build context: services/api (see compose.yaml).
FROM python:3.14-slim

# git for cloning; the Docker CLI and buildx talk to the host's daemon
# through the socket mounted in compose.yaml.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
COPY --from=docker:29-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker:29-cli /usr/local/libexec/docker/cli-plugins/docker-buildx /usr/local/libexec/docker/cli-plugins/docker-buildx

# The code imports from services/api's root (e.g. "from services.queue import ...").
WORKDIR /app/services/api

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "worker"]
