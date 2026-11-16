#!/usr/bin/env bash
# Runs ON THE VPS, called by the deploy job in .github/workflows/ci.yml.
# Deploys one exact commit:  bash scripts/deploy.sh <commit sha>
set -euo pipefail

main() {
    local sha="${1:?usage: deploy.sh <commit sha>}"
    local compose="docker compose --profile prod --profile workers"

    cd /opt/syphership

    echo "==> Checking out $sha"
    git fetch --quiet origin main
    git reset --hard "$sha"

    echo "==> Building images"
    $compose build

    echo "==> Running database migrations"
    $compose run --rm api alembic upgrade head

    echo "==> Restarting containers"
    $compose up -d

    echo "==> Waiting for the API"
    for _ in $(seq 1 30); do
        if curl -fsS localhost:8000/ready; then
            echo
            echo "==> Deployed $sha"
            return 0
        fi
        sleep 2
    done

    echo "API did not become ready in 60 seconds" >&2
    $compose logs --tail 50 api >&2
    return 1
}

# Wrapped in main() on purpose: "git reset" above can replace this very file,
# and bash reads a script while it runs. A function is read in full first.
main "$@"
