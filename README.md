# Grafana PDF Reporter

[![CI](https://github.com/Blanqui04/SOME-REPORTING-PDF/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Blanqui04/SOME-REPORTING-PDF/actions/workflows/ci.yml)

Aplicación web completa para generar informes PDF de dashboards de Grafana de forma manual o automatizada.

## Funcionalidades

| Funcionalidad | Estado |
|---|---|
| Autenticación JWT (login + registro) | ✅ |
| LDAP / Active Directory + TOTP 2FA | ✅ |
| RBAC (admin / editor / viewer) | ✅ |
| Integración completa Grafana API | ✅ |
| Generación PDF avanzada (WeasyPrint + Jinja2) | ✅ |
| Plantillas PDF personalizables con overlay | ✅ |
| Taula de continguts (TOC), marca d'aigua, orientació | ✅ |
| Comparació temporal, taules de dades, grid layout | ✅ |
| Xifrat PDF (AES-256) | ✅ |
| Programació automàtica (Celery + Redis, cron) | ✅ |
| Frontend React + Tailwind amb mode fosc | ✅ |
| i18n 4 idiomes (CA / ES / EN / PL) | ✅ |
| Notificacions Slack / Teams (webhooks) | ✅ |
| Emmagatzematge S3 / MinIO | ✅ |
| Eina CLI | ✅ |
| Mètriques Prometheus | ✅ |
| Compressió PDF | ✅ |
| Generació en batch | ✅ |
| Cache de panells (Redis) | ✅ |
| Filtre per tags, estadístiques, preview PDF | ✅ |
| Toast notifications, rate limiting, audit log | ✅ |
| 230 tests (pytest), ruff, mypy | ✅ |
| CI/CD GitHub Actions | ✅ |
| Docker + docker-compose (5 serveis) | ✅ |

## Stack tècnic

| Component | Tecnologia |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.x, PostgreSQL 16 |
| Auth | JWT (python-jose) + LDAP (ldap3) + TOTP (pyotp) |
| PDF | WeasyPrint + Jinja2 + pypdf (overlay, xifrat, compressió) |
| Tasques | Celery 5.x + Redis 7 |
| Frontend | React 18 + Vite 5 + Tailwind CSS 3 |
| Infra | Docker + docker-compose + GitHub Actions |
| Mètriques | Prometheus (endpoint `/metrics`) |

## Estructura del projecte

```
backend/
├── app/
│   ├── api/v1/         # Endpoints REST (auth, grafana, reports, schedules, templates, audit, i18n)
│   ├── core/           # Config, security, middleware, rate limiting, metrics, i18n, permissions
│   ├── models/         # SQLAlchemy models (user, report, schedule, template, audit)
│   ├── schemas/        # Pydantic v2 schemas
│   ├── services/       # Business logic (auth, grafana, pdf, reports, notifications, storage, cache)
│   ├── tasks/          # Celery tasks (report generation, schedules)
│   └── templates/      # Jinja2 + CSS templates for PDF
├── cli.py              # Command-line interface
├── tests/              # 230 tests (pytest)
└── requirements.txt
frontend/
├── src/
│   ├── api/            # HTTP client (Axios)
│   ├── components/     # Reusable components (Layout, Toast, ThemeToggle, etc.)
│   ├── context/        # React contexts (Auth, Language, Theme)
│   ├── i18n/           # Translations (4 languages)
│   └── pages/          # Page components (Login, Dashboards, Reports, Stats, etc.)
└── package.json
```

## Requisits previs

- Python 3.12+
- Node.js 18+
- PostgreSQL 16+ (o Docker)
- Redis 7+ (o Docker)

## Configuració local

### 1) Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Crea un fitxer `.env` amb les variables requerides:

```env
POSTGRES_PASSWORD=your_password
JWT_SECRET_KEY=your_secret_key
GRAFANA_URL=http://your-grafana:3000
GRAFANA_API_KEY=your_grafana_api_key
```

### 2) Migracions

```bash
alembic upgrade head
```

### 3) Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4) Executar backend

```bash
uvicorn backend.app.main:app --reload
```

### 5) Workers Celery

```bash
celery -A backend.app.celery_app:celery worker -l info
celery -A backend.app.celery_app:celery beat -l info
```

## Executar amb Docker

```bash
docker compose up --build
```

Aixeca 5 serveis: `app` (FastAPI), `postgres`, `redis`, `celery-worker`, `celery-beat`.

## CLI

```bash
# Llistar dashboards
python -m backend.cli -u admin -p password dashboards

# Generar informe amb espera
python -m backend.cli -u admin -p password generate -d <dashboard_uid> --wait -o report.pdf

# Llistar informes
python -m backend.cli -u admin -p password list --status completed

# Descarregar informe
python -m backend.cli -u admin -p password download <report_id> -o output.pdf

# Estadístiques
python -m backend.cli -u admin -p password stats --json
```

## Qualitat i proves

```bash
# Tests (230 tests)
POSTGRES_PASSWORD=test JWT_SECRET_KEY=test GRAFANA_URL=http://localhost:3000 GRAFANA_API_KEY=test \
  pytest -q

# Linting
ruff check backend/

# Type checking (80 source files)
mypy backend/
```

## API Endpoints principals

| Mètode | Path | Descripció |
|---|---|---|
| `POST` | `/api/v1/auth/login` | Autenticació JWT |
| `POST` | `/api/v1/auth/register` | Registre d'usuari |
| `POST` | `/api/v1/auth/totp/setup` | Configurar 2FA |
| `GET` | `/api/v1/grafana/dashboards` | Llistar dashboards |
| `GET` | `/api/v1/grafana/dashboards/{uid}` | Detall dashboard |
| `POST` | `/api/v1/reports/generate` | Generar informe PDF |
| `POST` | `/api/v1/reports/batch` | Generació en batch |
| `GET` | `/api/v1/reports` | Llistar informes |
| `GET` | `/api/v1/reports/stats` | Estadístiques |
| `GET` | `/api/v1/reports/{id}/download` | Descarregar PDF |
| `DELETE` | `/api/v1/reports/{id}` | Eliminar informe |
| `GET/POST` | `/api/v1/schedules` | Gestió programacions |
| `GET/POST` | `/api/v1/templates` | Gestió plantilles |
| `GET` | `/api/v1/audit` | Log d'auditoria (admin) |
| `GET` | `/api/v1/i18n/{lang}` | Traduccions |
| `GET` | `/health` | Health check |
| `GET` | `/metrics` | Mètriques Prometheus |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc API docs |

## Variables d'entorn

| Variable | Descripció | Per defecte |
|---|---|---|
| `POSTGRES_PASSWORD` | Contrasenya PostgreSQL | *(requerit)* |
| `JWT_SECRET_KEY` | Secret per tokens JWT | *(requerit)* |
| `GRAFANA_URL` | URL base de Grafana | *(requerit)* |
| `GRAFANA_API_KEY` | API key de Grafana | *(requerit)* |
| `REDIS_URL` | URL Redis | `redis://localhost:6379/0` |
| `CELERY_BROKER_URL` | URL broker Celery | `redis://localhost:6379/1` |
| `LDAP_ENABLED` | Activar LDAP/AD | `false` |
| `TOTP_ENABLED` | Activar 2FA | `false` |
| `S3_ENABLED` | Activar emmagatzematge S3 | `false` |
| `PROMETHEUS_ENABLED` | Activar mètriques | `false` |
| `WEBHOOK_SLACK_URL` | URL webhook Slack | *(buit)* |
| `WEBHOOK_TEAMS_URL` | URL webhook Teams | *(buit)* |

## Integració contínua (CI)

GitHub Actions workflow a `.github/workflows/ci.yml`:

- **Frontend**: `npm ci` + `npm run build`
- **Lint**: `ruff check` + `ruff format --check` + `mypy`
- **Test**: PostgreSQL de servei + `pytest`
- Caché de dependències pip per reduir temps
