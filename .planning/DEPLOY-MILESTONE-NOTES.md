# Deploy Milestone — Decisiones capturadas (2026-06-14)

Objetivo: deployar a Railway (backend + Postgres) + Vercel (frontend) con CI/CD de GitHub Actions.
Capturado al final de una sesión larga (contexto ~73%); arrancar fresco con /clear → /gsd:new-milestone.

## Decisiones tomadas por el usuario
- **Cuentas:** ya tiene Railway y Vercel (VAPAI-Studio). El usuario hace los pasos de login/autorización cuando se le indique.
- **Secrets:** tiene OPENAI_API_KEY, ANTHROPIC_API_KEY a mano; genera SECRET_KEY. Los carga él en Railway (nunca en el repo).
- **Media/uploads:** VOLUMEN PERSISTENTE de Railway montado en /media (no efímero).
- **CI/CD trigger:** push a `main` = deploy a prod (backend Railway + frontend Vercel). Simple/directo.
- **DB:** PENDIENTE DE CONFIRMAR — aclarado que es UNA sola Postgres con TODA la data (proyectos, guiones, usuarios, api_keys + embeddings de agentes/RAG con pgvector), no una base separada de agentes. Recomendación: Railway Postgres (un proveedor, latencia mínima, DATABASE_URL automática). Alternativa: Supabase (mejor panel, ya lo usa en otros proyectos, pero latencia backend↔db y un proveedor más). → CONFIRMAR ESTO PRIMERO en la próxima sesión.

## Hechos técnicos del repo (ya verificados)
- Backend: FastAPI, `Procfile` ya existe (`web: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`), `runtime.txt` presente.
- DB necesita **pgvector** (tablas concepts/book_chunks/agent_books). Railway y Supabase ambos lo soportan.
- Migraciones: `backend/migrations/delta/*.sql` idempotentes — hay que aplicarlas en prod (o init_db al arrancar).
- Frontend: Vite/React, `npm run build` = `tsc && vite build`. `API_BASE_URL = import.meta.env.VITE_API_URL || '/api'` (constants.ts:7) — parametrizable vía env.
- **Hardcodeos a localhost a parametrizar:** `ALLOWED_ORIGINS` (config.py + docker-compose), y la URL base del servidor MCP (`http://localhost:8001` en mcp_server/server.py — AuthSettings issuer/resource_server_url). El `/mcp` quedará público tras el deploy → ojo con DNS-rebinding (hoy off) y CORS.
- SECRET_KEY: config.py YA valida que no sea el default en producción (raise ValueError) — bien.
- No hay `.github/workflows/` todavía. CI actual: ninguno.
- Tests: ~399 pasan (4 flakes pre-existentes documentados). Útil como gate de CI.

## Alcance estimado del milestone (para el roadmap)
1. Dockerfile de producción para el backend (o usar el Procfile + nixpacks de Railway).
2. Parametrizar localhost → env vars (ALLOWED_ORIGINS, VITE_API_URL, MCP base URL).
3. Railway: backend service + Postgres (pgvector) + volumen /media + env vars (secrets).
4. Vercel: frontend, VITE_API_URL → dominio del backend de Railway.
5. Migraciones en prod (aplicar delta/ o init_db on boot).
6. GitHub Actions: tests en push + deploy a Railway y Vercel en merge a main.
7. CORS/MCP: ALLOWED_ORIGINS al dominio de Vercel; revisar DNS-rebinding del MCP ahora que es público.

## Deuda v8.0 que sigue pendiente (no bloquea el deploy)
- Bug del enum `framework` (pre-existente, roto en Postgres app-wide).
- Confirmar pin de dependencias con `docker compose build` limpio.
- Verificar Hermes (header estático).
