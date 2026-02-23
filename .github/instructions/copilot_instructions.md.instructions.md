# GitHub Copilot Instructions - Grafana PDF Reporter

## 🎯 Project Overview

This is a **Grafana PDF Reporter** application that automates generation of customized PDF reports from Grafana dashboards using their HTTP API. The native Grafana reporting feature is unavailable in the user's version, so this tool fills that gap.

**Primary Goals:**
- Consume Grafana data via HTTP API (no native reporting dependency)
- Generate customized PDF reports with configurable templates
- Automate report generation (scheduled or manual trigger)
- Manage user authentication and dashboard permissions
- Production-ready with Docker deployment

---

## 🛠️ Tech Stack (MANDATORY)

| Component | Technology | Version |
|-----------|-----------|---------|
| Backend | Python + FastAPI | 3.11+ |
| Database | PostgreSQL + SQLAlchemy | 2.x |
| PDF Engine | WeasyPrint + Jinja2 | Latest |
| Auth | JWT (HS256) | python-jose |
| Task Queue | APScheduler or Celery+Redis | Latest |
| Frontend | React + Vite + Tailwind | MVP: HTMX acceptable |
| DevOps | Docker + docker-compose + GitHub Actions | Latest |

---

## 📋 Coding Standards

### Python Guidelines
- ✅ **Type hints everywhere** (Python 3.11+ syntax)
- ✅ **Docstrings** in Google style for all public functions/classes
- ✅ **Pydantic v2** for all data validation and settings
- ✅ **FastAPI best practices**: dependency injection, `Annotated`, `BackgroundTasks`
- ✅ **Error handling**: Custom exceptions, proper logging (no `print()`)
- ✅ **Async/await** where appropriate (I/O operations)

### Example Function Structure
```python
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def process_data(param: str, count: int = 10) -> dict:
    """
    Process data with validation.
    
    Args:
        param: Input parameter description
        count: Number of iterations (default: 10)
    
    Returns:
        dict: Processed result with status and data
    
    Raises:
        ValueError: If param is empty
        RuntimeError: If processing fails
    """
    if not param:
        raise ValueError("param cannot be empty")
    
    try:
        result = {"status": "success", "data": []}
        logger.info(f"Processing {count} items for {param}")
        return result
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        raise RuntimeError(f"Processing error: {e}")