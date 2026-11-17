#!/usr/bin/env bash
set -euo pipefail

echo "=== DreamsAdverstings Production Bootstrap ==="
if [ ! -f .env ]; then
  echo "ERROR: .env file not found. Copy .env.example to .env and configure secrets first."
  exit 1
fi

echo "1. Creating pre-deployment PostgreSQL backup..."
./scripts/backup_db.sh || echo "Skipping initial backup if DB is fresh."

echo "2. Building & starting production containers (Nginx, Frontend, Backend, Automation Worker, Postgres, Redis)..."
docker compose -f docker-compose.prod.yml up -d --build

echo "3. Verifying API healthcheck..."
sleep 5
curl -fsS http://localhost/api/v1/health && echo ""
echo "=== Deployment Complete ==="
