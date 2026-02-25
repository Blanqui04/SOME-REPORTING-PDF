# Roadmap: Futures Actualitzacions i Millores

**Versió actual:** 3.0.0 (i18n, plantilles, 102 tests)  
**Data:** 2026-02-24  
**Autor:** Magicinfo

---

## Resum de l'estat actual

| Funcionalitat | Estat |
|---|---|
| Autenticació JWT (login + registre) | ✅ Complet |
| Integració Grafana API | ✅ Complet |
| Generació PDF (WeasyPrint + Jinja2) | ✅ Complet |
| Plantilles PDF personalitzables | ✅ Complet |
| Overlay PDF base (pypdf) | ✅ Complet |
| Render paral·lel de panells | ✅ Complet |
| i18n 4 idiomes (CA/ES/EN/PL) | ✅ Complet |
| Frontend React + Tailwind | ✅ Complet |
| 102 tests (pytest) | ✅ Complet |
| CI/CD GitHub Actions | ✅ Complet |
| Scheduler automàtic | ❌ Pendent |

---

## 🗺️ Fases Futures

### Fase 1 — Automatització i Programació (Prioritat Alta)

| # | Tasca | Descripció |
|---|---|---|
| 1.1 | **Scheduler APScheduler** | Integrar APScheduler per programar generació periòdica de reports (diari, setmanal, mensual) |
| 1.2 | **CRUD schedules** | API endpoints per crear, editar, eliminar i llistar programacions |
| 1.3 | **UI programació** | Pàgina frontend per gestionar programacions amb selector de cron/interval |
| 1.4 | **Enviament per email** | SMTP integrat per enviar PDF per email automàticament un cop generat |
| 1.5 | **Webhooks** | Notificacions push a URLs externes quan un report finalitza |

### Fase 2 — Millores de Seguretat i Infraestructura

| # | Tasca | Descripció |
|---|---|---|
| 2.1 | **Rols d'usuari (RBAC)** | Implementar sistema de rols (admin, editor, viewer) amb permisos granulars |
| 2.2 | **Autenticació OAuth2/SSO** | Suport per login via Google, GitHub, LDAP o OpenID Connect |
| 2.3 | **Rate limiting** | Limitar peticions per IP/usuari (slowapi o similar) |
| 2.4 | **Xifrat PDF** | Opció per protegir PDFs generats amb contrasenya |
| 2.5 | **Audit log** | Registre de totes les accions (generació, descàrrega, canvis de configuració) |
| 2.6 | **2FA/TOTP** | Autenticació de dos factors per comptes sensibles |

### Fase 3 — Millores del Motor PDF

| # | Tasca | Descripció |
|---|---|---|
| 3.1 | **Taula de continguts** | TOC automàtic als PDFs amb links interns als panells |
| 3.2 | **Gràfics vectorials (SVG)** | Exportar panells com SVG en lloc de PNG per major qualitat |
| 3.3 | **Landscape/Portrait** | Selecció d'orientació per pàgina o per panell |
| 3.4 | **Layout personalitzable** | Drag & drop per organitzar panells dins el PDF (grid configurable) |
| 3.5 | **Taula de dades** | Incloure les dades raw dels panells com a taula annexa al PDF |
| 3.6 | **Comparació temporal** | PDFs amb dues franges horàries costat a costat |
| 3.7 | **Marca d'aigua** | Marca d'aigua configurable ("Confidencial", "Esborrany") |

### Fase 4 — Millores del Frontend

| # | Tasca | Descripció |
|---|---|---|
| 4.1 | **Dashboard d'estadístiques** | Pàgina principal amb mètriques: reports generats, errors, ús per dashboard |
| 4.2 | **Vista prèvia del PDF** | Preview inline del PDF abans de descarregar (PDF.js) |
| 4.3 | **Mode fosc** | Tema dark mode per tota la interfície |
| 4.4 | **PWA** | Progressive Web App per accés offline i notificacions push |
| 4.5 | **Drag & drop panells** | Ordenar panells amb drag & drop abans de generar |
| 4.6 | **Filtre per tags** | Filtrar dashboards per tags de Grafana |
| 4.7 | **Comparació de reports** | Vista side-by-side per comparar dos PDFs |
| 4.8 | **Notificacions in-app** | Toast notifications per estat de generació en temps real (WebSocket) |

### Fase 5 — Integració i Ecosistema

| # | Tasca | Descripció |
|---|---|---|
| 5.1 | **API pública documentada** | OpenAPI/Swagger amb exemples i playground |
| 5.2 | **Plugin Grafana** | Panel/plugin natiu de Grafana per llançar reports des del propi dashboard |
| 5.3 | **Integració Slack/Teams** | Enviar PDFs directament a canals de Slack o Microsoft Teams |
| 5.4 | **S3/MinIO storage** | Emmagatzemar PDFs en objectes S3 en lloc de PostgreSQL (escalabilitat) |
| 5.5 | **Multi-tenant** | Suport per múltiples organitzacions amb aïllament de dades |
| 5.6 | **Grafana Alerting** | Generar report automàtic quan salta una alerta |
| 5.7 | **CLI tool** | Eina de línia de comandes per generar reports via terminal |

### Fase 6 — Rendiment i Escalabilitat

| # | Tasca | Descripció |
|---|---|---|
| 6.1 | **Celery/Redis** | Migrar background tasks a Celery amb Redis per millor control de cues |
| 6.2 | **Cache de panells** | CDN/cache de les imatges de panells per evitar re-renders |
| 6.3 | **Kubernetes** | Helm chart per desplegament en K8s amb auto-scaling |
| 6.4 | **Compressió PDF** | Comprimir imatges dins el PDF per reduir mida |
| 6.5 | **Generació en batch** | Generar múltiples reports d'un sol cop (selecció múltiple de dashboards) |
| 6.6 | **Métriques Prometheus** | Exportar mètriques de l'aplicació per monitoring amb Grafana |

### Fase 7 — Qualitat i Documentació

| # | Tasca | Descripció |
|---|---|---|
| 7.1 | **E2E tests (Playwright)** | Tests end-to-end del frontend amb Playwright |
| 7.2 | **Load testing** | Tests de càrrega amb Locust per validar rendiment |
| 7.3 | **Documentació d'usuari** | Guia d'usuari completa amb captures de pantalla |
| 7.4 | **Documentació d'API** | Redoc/Swagger amb exemples per a cada endpoint |
| 7.5 | **Contributing guide** | Guia per contributors externs amb estil de codi i workflow |
| 7.6 | **Changelog automàtic** | Generació automàtica de CHANGELOG des dels commits convencionals |

---

## 📊 Prioritat Suggerida

```
Sprint 1 (pròxim):    1.1, 1.2, 1.3         (Scheduler)
Sprint 2:             1.4, 2.1, 4.1          (Email + RBAC + Dashboard stats)
Sprint 3:             3.1, 3.3, 4.2, 5.1     (PDF millores + Preview + API docs)
Sprint 4:             5.2, 5.3, 2.2          (Plugin Grafana + Slack + OAuth)
Sprint 5:             6.1, 6.2, 4.3, 4.8     (Celery + Cache + Dark mode + WS)
Sprint 6:             7.1, 7.2, 6.3          (E2E + Load + K8s)
```

---

## 🔧 Deute tècnic pendent

| Tasca | Impacte |
|---|---|
| Eliminar `--reload` del Dockerfile CMD | 🔴 Producció |
| Afegir usuari non-root al Dockerfile | 🔴 Seguretat |
| Timeout configurable a `generate_report_task` | 🟡 Fiabilitat |
| Request ID middleware per traçabilitat | 🟡 Debugging |
| Migrar tests a PostgreSQL real (testcontainers) | 🟡 Fidelitat |
| Afegir `.dockerignore` | 🟢 Build |
