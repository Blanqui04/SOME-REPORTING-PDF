"""Internationalization API endpoints."""

from fastapi import APIRouter

from backend.app.core.i18n import SUPPORTED_LOCALES, get_locale_name, get_translations

router = APIRouter(prefix="/i18n", tags=["i18n"])


@router.get("/locales")
def list_locales() -> list[dict[str, str]]:
    """Return supported locales with display names.

    Returns:
        List of locale objects with ``code`` and ``name`` fields.
    """
    return [{"code": loc, "name": get_locale_name(loc)} for loc in SUPPORTED_LOCALES]


@router.get("/translations/{locale}")
def get_locale_translations(locale: str) -> dict[str, str]:
    """Return all translation strings for a locale.

    Falls back to default locale if unknown.

    Args:
        locale: ISO 639-1 language code.

    Returns:
        Dictionary of translation keys to localized strings.
    """
    return get_translations(locale)
