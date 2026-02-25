# Planning: Grafana PDF Reporter

**Versió:** 2.0.0  
**Estat:** En execució  
**Data:** 2026-02-24  
**Autor:** Magicinfo

---

## 🎯 Objectiu del Projecte

Desenvolupar una aplicació web que:

1. **Consumi dades de Grafana** via HTTP API (sense dependre del reporting natiu).
2. **Generi reports PDF personalitzats** amb plantilles configurables.
3. **Automatitzi la generació** (programació periòdica o trigger manual).
4. **Gestioni autenticació d'usuaris** i permisos per a dashboards.
5. **Estigui preparat per a desplegament** amb Docker i CI/CD.

---

## 🗓️ Estat de les Fases Originals

| Fase | Estat | Notes |
|------|-------|-------|
| 1. Setup | ✅ Complet | Repo, Docker, CI amb GitHub Actions |
| 2. Core Backend | ✅ Complet | Auth JWT, GrafanaClient, endpoints CRUD |
| 3. PDF Engine | ✅ Complet | Jinja2 + WeasyPrint, templates CSS |
| 4. Frontend mínim | ✅ Complet | React + Vite + Tailwind, login/dashboards/reports |
| 5. Automatització | ❌ Pendent | Scheduler, email — model stub creat |
| 6. Hardening | 🟡 Parcial | Tests OK (41 passed), CI OK, docs parcials |

---

## 📋 Pla de Millores (Sprint Actual)

### Fase A — Seguretat i Infraestructura

| # | Tasca | Prioritat | Estat |
|---|-------|-----------|-------|
| A1 | Eliminar --reload del Dockerfile CMD | 🔴 Alta | ⬜ |
| A2 | Afegir usuari non-root al Dockerfile | 🔴 Alta | ⬜ |
| A3 | Crear .dockerignore | 🔴 Alta | ⬜ |
| A4 | GrafanaClient com singleton amb tancament al lifespan | 🔴 Alta | ⬜ |

### Fase B — Backend Features

| # | Tasca | Prioritat | Estat |
|---|-------|-----------|-------|
| B1 | Endpoint DELETE /api/v1/reports/{id} | 🔴 Alta | ⬜ |
| B2 | Migració: índexs + ON DELETE CASCADE | 🔴 Alta | ⬜ |
| B3 | Request ID middleware per traçabilitat | 🟡 Mitjana | ⬜ |
| B4 | Timeout a generate_report_task | 🟡 Mitjana | ⬜ |
| B5 | Alembic compare_type=True | 🟡 Mitjana | ⬜ |

### Fase C — Frontend

| # | Tasca | Prioritat | Estat |
|---|-------|-----------|-------|
| C1 | Corregir errors silenciats a ReportsPage/ReportRow | 🔴 Alta | ⬜ |
| C2 | Ruta 404 catch-all amb pàgina d'error | 🔴 Alta | ⬜ |
| C3 | Formulari d'opcions al generar report | 🟡 Mitjana | ⬜ |
| C4 | Pàgina de registre d'usuaris | 🟡 Mitjana | ⬜ |
| C5 | Navegació responsive (hamburger mòbil) | 🟡 Mitjana | ⬜ |
| C6 | Axios timeout + router redirect 401 | 🟡 Mitjana | ⬜ |

### Fase D — Qualitat

| # | Tasca | Prioritat | Estat |
|---|-------|-----------|-------|
| D1 | Tests unitaris per security.py | 🟡 Mitjana | ⬜ |
| D2 | Validació final: tests + ruff + mypy | 🔴 Alta | ⬜ |

---

## 🧱 Arquitectura Tècnica

```
User → Frontend (React/Vite) → Backend (FastAPI)
                                    ├── Auth (JWT)
                                    ├── GrafanaClient (httpx → Grafana API)
                                    ├── PDF Engine (Jinja2 + WeasyPrint)
                                    ├── Report Service → PostgreSQL
                                    └── [Pendent] Scheduler (APScheduler)
```

---

## 📊 Mètriques de Qualitat Objectiu

| Mètrica | Actual | Objectiu |
|---------|--------|----------|
| Tests backend | 41 passed | 50+ passed |
| Ruff | 0 errors | 0 errors |
| Mypy | 0 errors | 0 errors |
| .dockerignore | ❌ | ✅ |
| Non-root Docker | ❌ | ✅ |
| Singleton GrafanaClient | ❌ | ✅ |
| DELETE reports | ❌ | ✅ |
| Frontend 404 | ❌ | ✅ |
| Request ID logs | ❌ | ✅ |
