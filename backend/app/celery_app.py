"""Celery application factory and configuration."""

import logging

from celery import Celery  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


def create_celery_app() -> Celery:
    """Create and configure the Celery application.

    Reads broker and backend URLs from application settings and
    configures task serialization, autodiscovery, and timeouts.

    Returns:
        Configured Celery application instance.
    """
    from backend.app.api.deps import get_settings

    settings = get_settings()

    app = Celery(
        "grafana_reporter",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )

    app.conf.update(
        # Serialization
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        # Task execution
        task_soft_time_limit=settings.CELERY_TASK_TIMEOUT,
        task_time_limit=settings.CELERY_TASK_TIMEOUT + 60,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        # Result backend
        result_expires=3600,
        # Task routing
        task_default_queue="default",
        task_routes={
            "backend.app.tasks.report_tasks.*": {"queue": "reports"},
        },
    )

    # Auto-discover tasks in the tasks package
    app.autodiscover_tasks(["backend.app.tasks"])

    # Periodic tasks (Celery Beat)
    app.conf.beat_schedule = {
        "execute-due-schedules": {
            "task": "execute_due_schedules",
            "schedule": 60.0,  # every 60 seconds
        },
    }

    logger.info("Celery app configured with broker=%s", settings.CELERY_BROKER_URL)
    return app


celery_app = create_celery_app()
