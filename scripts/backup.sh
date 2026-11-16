#!/usr/bin/env bash
# Daily database backup. Runs on the VPS from cron (/etc/cron.d/syphership-backup).
# Run by hand:  bash /opt/syphership/scripts/backup.sh
set -euo pipefail

BACKUP_DIR=/var/backups/syphership
KEEP_DAYS=7

main() {
    mkdir -p "$BACKUP_DIR"
    chmod 700 "$BACKUP_DIR"

    local file
    file="$BACKUP_DIR/syphership-$(date -u +%Y-%m-%d_%H%M).dump"

    cd /opt/syphership

    # Dump inside the Postgres container, which already has the user and DB name.
    # Single quotes: the container expands these variables, not this shell.
    # shellcheck disable=SC2016
    docker compose exec -T postgres \
        sh -c 'pg_dump -U "$POSTGRES_USER" --format=custom "$POSTGRES_DB"' \
        > "$file.tmp"

    # Only a finished dump gets the real name.
    mv "$file.tmp" "$file"
    chmod 600 "$file"

    # Keep the last KEEP_DAYS days.
    find "$BACKUP_DIR" -name 'syphership-*.dump' -mtime +"$KEEP_DAYS" -delete

    echo "$(date -u +%FT%TZ) backup ok: $file ($(du -h "$file" | cut -f1))"
}

main "$@"
