#!/usr/bin/env bash
# Transfer the processed book library (embeddings + knowledge graph included)
# from the local docker DB to Railway WITHOUT reprocessing (Phase 1 close-out).
#
# Usage:
#   RAILWAY_DATABASE_URL="postgresql://...railway..." bash scripts/transfer_library_to_railway.sh
#
# Requires: local docker stack up; Railway DB migrated to the same schema level
# (pgvector enabled). The mock-auth owner_id is the same fixed UUID on both
# sides, so ownership carries over untouched.
#
# ⚠ DESTRUCTIVE on Railway: replaces ALL book data there (books, chunks,
#   concepts, relationships, snippets) and cascades agent_books links.
#   Agents themselves are NOT touched — relink books to agents afterwards by
#   running setup_format_agents.py against the Railway API.

set -euo pipefail

: "${RAILWAY_DATABASE_URL:?Set RAILWAY_DATABASE_URL (Railway Postgres connection string)}"

DUMP=/tmp/books_kg_dump.sql
LOCAL_CONTAINER=screenwriting-assistant-db-1

echo "==> 1/4 Dump local (5 tablas, embeddings incluidos)"
docker exec "$LOCAL_CONTAINER" pg_dump -U screenwriter -d screenwriter_db \
  --data-only --no-owner \
  -t books -t book_chunks -t concepts -t concept_relationships -t snippets \
  > "$DUMP"
echo "    $(du -h "$DUMP" | cut -f1) escritos en $DUMP"

echo "==> 2/4 Verificando schema remoto (tablas y pgvector)"
psql "$RAILWAY_DATABASE_URL" -tAc "
  SELECT CASE WHEN count(*) = 5 THEN 'OK' ELSE 'FALTAN TABLAS: ' || (5 - count(*)) END
  FROM information_schema.tables
  WHERE table_name IN ('books','book_chunks','concepts','concept_relationships','snippets');"
psql "$RAILWAY_DATABASE_URL" -tAc \
  "SELECT 'pgvector ' || CASE WHEN count(*)=1 THEN 'OK' ELSE 'AUSENTE' END FROM pg_extension WHERE extname='vector';"

echo "==> 3/4 Limpiando libros previos en Railway (TRUNCATE ... CASCADE)"
read -r -p "    Esto BORRA la biblioteca actual de Railway. ¿Continuar? [y/N] " ok
[[ "$ok" == "y" ]] || { echo "abortado"; exit 1; }
psql "$RAILWAY_DATABASE_URL" -c "TRUNCATE books CASCADE;"

echo "==> 4/4 Restaurando dump"
psql "$RAILWAY_DATABASE_URL" -v ON_ERROR_STOP=1 -f "$DUMP" > /dev/null

echo "==> Verificación final"
psql "$RAILWAY_DATABASE_URL" -c "
  SELECT (SELECT count(*) FROM books)    AS books,
         (SELECT count(*) FROM concepts) AS concepts,
         (SELECT count(*) FROM snippets) AS snippets,
         (SELECT count(*) FROM book_chunks) AS chunks;"

echo "Listo. Ahora re-vinculá agentes: API_URL=<railway-api-url> python scripts/setup_format_agents.py"
