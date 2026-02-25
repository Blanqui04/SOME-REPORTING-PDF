# SOME-REPORTING-PDF

[![CI](https://github.com/Blanqui04/SOME-REPORTING-PDF/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Blanqui04/SOME-REPORTING-PDF/actions/workflows/ci.yml)

Aplicación web para generar informes PDF de dashboards de Grafana de forma manual o automatizada.

## Estado del proyecto

El proyecto está en estado **MVP funcional**:

- API backend con autenticación JWT
- Integración con API HTTP de Grafana
- Renderizado de paneles y generación PDF (Jinja2 + WeasyPrint)
- Frontend React para login, dashboards y reportes
- Migraciones con Alembic
- Contenedorización con Docker

## Stack técnico

- Backend: Python 3.11+, FastAPI, SQLAlchemy 2.x, PostgreSQL
- Auth: JWT (`python-jose`) + hash de contraseñas (`passlib`)
- PDF: WeasyPrint + Jinja2
- Frontend: React + Vite + Tailwind CSS
- Infra: Docker + docker-compose

## Estructura

- `backend/`: API, modelos, servicios, migraciones y tests
- `frontend/`: SPA React (Vite)
- `Dockerfile`, `docker-compose.yml`: despliegue local

## Requisitos

- Python 3.11+
- Node.js 18+
- PostgreSQL (si ejecutas sin Docker)

## Configuración local

### 1) Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Configura variables de entorno (base de datos, secrets JWT, Grafana URL/API key) según tu entorno.

### 2) Migraciones

```bash
cd backend
alembic upgrade head
```

### 3) Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4) Ejecutar backend

```bash
cd backend
uvicorn app.main:app --reload
```

## Ejecutar con Docker

```bash
docker compose up --build
```

## Calidad y pruebas

Desde la raíz del repositorio:

```bash
./.venv/bin/python -m pytest -q
./.venv/bin/ruff check backend
./.venv/bin/mypy backend/app
```

## Integración continua (CI)

El repositorio incluye workflow en GitHub Actions en [.github/workflows/ci.yml](.github/workflows/ci.yml):

- Ejecuta en push a `main`, pull request contra `main` y ejecución manual.
- Job `frontend`: `npm ci` + `npm run build` para validar SPA React.
- Job `lint`: `ruff check`, `ruff format --check` y `mypy`.
- Job `test`: levanta PostgreSQL de servicio y ejecuta tests backend.
- Incluye caché de dependencias pip para reducir tiempos de ejecución.

## Endpoints principales

- `POST /api/v1/auth/login`: autenticación
- `GET /api/v1/grafana/dashboards`: listar dashboards
- `POST /api/v1/reports`: generar reporte
- `GET /health`: salud del servicio

## Próximas mejoras sugeridas

- Scheduler de reportes en background con reintentos
- Métricas/observabilidad (Prometheus + logs estructurados)
- CI/CD con lint + tests + build de imágenes
- Gestión de permisos por dashboard/rol
