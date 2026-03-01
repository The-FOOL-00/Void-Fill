#!/usr/bin/env bash
# =============================================================================
# VoidFill — PostgreSQL backup script
#
# Usage (manual):
#   DATABASE_URL=postgresql://user:pass@host:5432/dbname ./scripts/db_backup.sh
#
# Railway cron setup:
#   1. In Railway dashboard → New Service → Cron Job
#   2. Schedule: 0 3 * * *   (daily at 03:00 UTC)
#   3. Command: /app/scripts/db_backup.sh
#   4. The cron service must share the same DATABASE_URL env var.
#
# Storage options (set one):
#   BACKUP_DIR  — local filesystem path  (default: /tmp/voidfill-backups)
#                 On Railway: mount a Volume and set BACKUP_DIR to its path.
#   S3_BUCKET   — if set, upload to S3 instead (requires aws-cli in image)
#
# Retention: keeps the 7 most recent .sql.gz files in BACKUP_DIR.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATABASE_URL="${DATABASE_URL:?ERROR: DATABASE_URL is not set}"
BACKUP_DIR="${BACKUP_DIR:-/tmp/voidfill-backups}"
S3_BUCKET="${S3_BUCKET:-}"
KEEP_DAYS=7

TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
FILENAME="voidfill_${TIMESTAMP}.sql.gz"

# ---------------------------------------------------------------------------
# Ensure backup directory exists
# ---------------------------------------------------------------------------
mkdir -p "$BACKUP_DIR"

# ---------------------------------------------------------------------------
# Run pg_dump and compress
# ---------------------------------------------------------------------------
echo "[backup] Starting dump → ${FILENAME}"
pg_dump "$DATABASE_URL" \
  --no-password \
  --format=plain \
  --no-owner \
  --no-acl \
  | gzip > "${BACKUP_DIR}/${FILENAME}"

FILESIZE=$(du -sh "${BACKUP_DIR}/${FILENAME}" | cut -f1)
echo "[backup] Dump complete — ${FILESIZE}"

# ---------------------------------------------------------------------------
# Upload to S3 (optional)
# ---------------------------------------------------------------------------
if [[ -n "$S3_BUCKET" ]]; then
  echo "[backup] Uploading to s3://${S3_BUCKET}/${FILENAME}"
  aws s3 cp \
    "${BACKUP_DIR}/${FILENAME}" \
    "s3://${S3_BUCKET}/${FILENAME}" \
    --storage-class STANDARD_IA
  echo "[backup] S3 upload complete"
fi

# ---------------------------------------------------------------------------
# Prune old backups (keep last 7)
# ---------------------------------------------------------------------------
echo "[backup] Pruning backups older than ${KEEP_DAYS} days…"
find "$BACKUP_DIR" -name "voidfill_*.sql.gz" -mtime "+${KEEP_DAYS}" -delete
REMAINING=$(find "$BACKUP_DIR" -name "voidfill_*.sql.gz" | wc -l | tr -d ' ')
echo "[backup] Done — ${REMAINING} backup(s) retained in ${BACKUP_DIR}"
