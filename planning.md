# Planning: Grafana PDF Reporter

**Versió:** 1.0.0  
**Estat:** Draft  
**Data:** 2026-03-01  
**Autor:** Magicinfo

## 🎯 Objectiu del Projecte

Desenvolupar una aplicació web que:

1. **Consumi dades de Grafana** via HTTP API (sense dependre de la funcionalitat nativa de reporting).
2. **Generi reports PDF personalitzats** amb plantilles configurables (format SOME*).
3. **Automatitzi la generació** (programació periòdica o trigger manual).
4. **Gestioni autenticació d'usuaris** i permisos per a dashboards.
5. **Estigui preparat per a desplegament** en un repositori dedicat de GitHub.

> *\*Nota: Confirmar especificacions del format "SOME" amb l'equip.*

---

## 🗓️ Cronograma per Fases

| Fase | Durada | Deliverables | Tasques Clau |
|------|--------|-------------|--------------|
| **1. Setup** | 2 dies | Repo, Docker, envs | `docker-compose.yml`, estructura de carpetes, variables d'entorn (.env), CI bàsic |
| **2. Core Backend** | 4 dies | API funcional | Auth (JWT), `GrafanaClient` wrapper, endpoint `/api/reports/generate`, logs |
| **3. PDF Engine** | 3 dies | Templates Jinja2, generació PDF | Integració WeasyPrint, CSS per a impressió, gestió d'imatges (panells), metadades dinàmiques |
| **4. Frontend mínim** | 3 dies | UI configuració reports | Form per seleccionar dashboard/panells, freqüència, destinataris; llistat de reports generats |
| **5. Automatització** | 2 dies | Scheduler, webhooks | APScheduler/Celery per execució periòdica, notificacions email, emmagatzematge (S3/local) |
| **6. Hardening** | 2 dies | Tests, docs, deploy | Tests unitaris/integració, documentació API (OpenAPI), secrets management, README |

---

## 🧱 Arquitectura Tècnica

```mermaid
flowchart LR
    User[Usuari] --> Frontend[Frontend: React/HTMX]
    Frontend --> API[Backend: FastAPI]
    API --> Auth[Auth: JWT/OAuth2]
    API --> Grafana[GrafanaClient Service]
    Grafana --> GrafanaInst[(Grafana API)]
    API --> PDF[PDF Generator: WeasyPrint+Jinja2]
    PDF --> Storage[(PostgreSQL/S3)]
    API --> Scheduler[APScheduler/Celery]
    Scheduler --> Email[SendGrid/SMTP]
    
    style GrafanaInst fill:#e1f5fe
    style Storage fill:#e8f5e9