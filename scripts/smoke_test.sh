#!/usr/bin/env bash
#
# Post-deploy smoke test (DVER-01). Confirms production is actually live before
# a deploy is considered successful:
#   1. Backend /health responds 200 at the Railway domain.
#   2. The deployed frontend loads (200) at the Vercel domain.
#
# Usage:
#   BACKEND_URL=https://<svc>.up.railway.app FRONTEND_URL=https://<app>.vercel.app \
#     scripts/smoke_test.sh
#
# Exits non-zero (failing the deploy) if either check fails. Retries each target
# a few times to absorb cold-start / propagation delay.

set -euo pipefail

BACKEND_URL="${BACKEND_URL:?BACKEND_URL must be set (Railway backend domain)}"
FRONTEND_URL="${FRONTEND_URL:?FRONTEND_URL must be set (Vercel frontend domain)}"

RETRIES="${SMOKE_RETRIES:-10}"
DELAY="${SMOKE_DELAY:-6}"

check() {
  local name="$1" url="$2"
  local i status
  for i in $(seq 1 "$RETRIES"); do
    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "$url" || echo "000")
    if [ "$status" = "200" ]; then
      echo "✓ ${name} OK (200) — ${url}"
      return 0
    fi
    echo "… ${name} attempt ${i}/${RETRIES} got ${status} — retrying in ${DELAY}s"
    sleep "$DELAY"
  done
  echo "✗ ${name} FAILED after ${RETRIES} attempts — ${url}" >&2
  return 1
}

echo "== Post-deploy smoke test =="
check "backend /health" "${BACKEND_URL%/}/health"
check "frontend"        "$FRONTEND_URL"
echo "== Smoke test passed: production is live =="
