#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p "$BACKUP_DIR"

PGHOST="${POSTGRES_HOST:-localhost}"
PGPORT="${POSTGRES_PORT:-5432}"
PGUSER="${POSTGRES_USER:-dreams_user}"
PGDB="${POSTGRES_DB:-dreamsadverstings_db}"

BACKUP_FILE="$BACKUP_DIR/${PGDB}_pre_upgrade_${TIMESTAMP}.dump"
echo "Creating PostgreSQL custom-format backup at $BACKUP_FILE ..."
pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -F c -b -v -f "$BACKUP_FILE" "$PGDB"
echo "Backup completed successfully: $BACKUP_FILE"
