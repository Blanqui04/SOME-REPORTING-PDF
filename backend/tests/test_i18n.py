"""Tests for the internationalization (i18n) module and API endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.app.core.i18n import (
    _TRANSLATIONS,
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    get_locale_name,
    get_translations,
    t,
)

# ---------------------------------------------------------------------------
# Unit tests for i18n core module
# ---------------------------------------------------------------------------


class TestSupportedLocales:
    """Tests for locale configuration constants."""

    def test_four_locales_defined(self) -> None:
        """Exactly 4 supported locales are configured."""
        assert len(SUPPORTED_LOCALES) == 4

    def test_expected_locale_codes(self) -> None:
        """All expected locale codes (ca, es, en, pl) are present."""
        assert set(SUPPORTED_LOCALES) == {"ca", "es", "en", "pl"}

    def test_default_locale_is_catalan(self) -> None:
        """Default locale defaults to Catalan."""
        assert DEFAULT_LOCALE == "ca"

    def test_default_locale_in_supported(self) -> None:
        """Default locale is within supported locales."""
        assert DEFAULT_LOCALE in SUPPORTED_LOCALES


class TestTranslationCompleteness:
    """Tests ensuring all locales have the same set of translation keys."""

    def test_all_locales_have_translations(self) -> None:
        """Every supported locale has an entry in the translations dict."""
        for locale in SUPPORTED_LOCALES:
            assert locale in _TRANSLATIONS, f"Missing translations for locale '{locale}'"

    def test_all_locales_have_same_keys(self) -> None:
        """All locale dictionaries have identical sets of keys."""
        ca_keys = set(_TRANSLATIONS["ca"].keys())
        for locale in SUPPORTED_LOCALES:
            locale_keys = set(_TRANSLATIONS[locale].keys())
            missing = ca_keys - locale_keys
            extra = locale_keys - ca_keys
            assert not missing, f"Locale '{locale}' missing keys: {missing}"
            assert not extra, f"Locale '{locale}' has extra keys: {extra}"

    def test_no_empty_translations(self) -> None:
        """No translation value is an empty string."""
        for locale in SUPPORTED_LOCALES:
            for key, value in _TRANSLATIONS[locale].items():
                assert value.strip(), f"Empty translation: '{locale}'.'{key}'"

    def test_pdf_keys_present(self) -> None:
        """Core PDF label keys exist in every locale."""
        required_keys = [
            "pdf.title",
            "pdf.dashboard_label",
            "pdf.dashboard_uid",
            "pdf.generated_at",
            "pdf.time_range",
            "pdf.panels_included",
            "pdf.panels_section",
            "pdf.image_not_available",
            "pdf.footer_default",
            "pdf.page",
        ]
        for locale in SUPPORTED_LOCALES:
            for key in required_keys:
                assert key in _TRANSLATIONS[locale], (
                    f"Locale '{locale}' missing required key '{key}'"
                )

    def test_status_keys_present(self) -> None:
        """Status translation keys exist for all locales."""
        statuses = ["pending", "generating", "completed", "failed"]
        for locale in SUPPORTED_LOCALES:
            for status in statuses:
                key = f"status.{status}"
                assert key in _TRANSLATIONS[locale], (
                    f"Locale '{locale}' missing status key '{key}'"
                )

    def test_panel_type_keys_present(self) -> None:
        """Panel type translation keys exist for all locales."""
        panel_types = [
            "graph", "timeseries", "table", "stat", "gauge",
            "barchart", "piechart", "text", "bargauge", "heatmap", "geomap",
        ]
        for locale in SUPPORTED_LOCALES:
            for ptype in panel_types:
                key = f"panel.{ptype}"
                assert key in _TRANSLATIONS[locale], (
                    f"Locale '{locale}' missing panel key '{key}'"
                )


class TestGetTranslations:
    """Tests for get_translations() function."""

    @pytest.mark.parametrize("locale", SUPPORTED_LOCALES)
    def test_returns_dict_for_valid_locale(self, locale: str) -> None:
        """get_translations returns a non-empty dict for valid locales."""
        result = get_translations(locale)
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_fallback_for_unknown_locale(self) -> None:
        """Unknown locale falls back to default (Catalan)."""
        result = get_translations("xx")
        assert result == _TRANSLATIONS[DEFAULT_LOCALE]

    def test_returns_correct_locale(self) -> None:
        """English translations are different from Catalan."""
        en = get_translations("en")
        ca = get_translations("ca")
        assert en["pdf.generated_at"] == "Generated at"
        assert ca["pdf.generated_at"] == "Generat el"


class TestTFunction:
    """Tests for t() single-key translation helper."""

    def test_translates_known_key(self) -> None:
        """t() returns correct translation for a known key."""
        assert t("pdf.title", "en") == "Report"
        assert t("pdf.title", "es") == "Informe"
        assert t("pdf.title", "pl") == "Raport"
        assert t("pdf.title", "ca") == "Informe"

    def test_unknown_key_returns_key(self) -> None:
        """t() returns the key itself when not found."""
        result = t("nonexistent.key", "en")
        assert result == "nonexistent.key"

    def test_default_locale_is_catalan(self) -> None:
        """t() with no explicit locale uses Catalan."""
        result = t("pdf.generated_at")
        assert result == "Generat el"

    @pytest.mark.parametrize("locale", SUPPORTED_LOCALES)
    def test_status_translations_differ_from_key(self, locale: str) -> None:
        """Status translations are not just the raw key."""
        result = t("status.completed", locale)
        assert result != "status.completed"


class TestGetLocaleName:
    """Tests for get_locale_name() function."""

    def test_catalan_name(self) -> None:
        assert get_locale_name("ca") == "Català"

    def test_spanish_name(self) -> None:
        assert get_locale_name("es") == "Español"

    def test_english_name(self) -> None:
        assert get_locale_name("en") == "English"

    def test_polish_name(self) -> None:
        assert get_locale_name("pl") == "Polski"

    def test_unknown_returns_code(self) -> None:
        """Unknown locale code returns the code itself."""
        assert get_locale_name("xx") == "xx"


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestI18nAPILocales:
    """Tests for GET /api/v1/i18n/locales."""

    def test_list_locales(self, client: TestClient) -> None:
        """Locales endpoint returns all 4 locales."""
        response = client.get("/api/v1/i18n/locales")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        codes = {item["code"] for item in data}
        assert codes == {"ca", "es", "en", "pl"}

    def test_locales_have_names(self, client: TestClient) -> None:
        """Each locale has a non-empty name field."""
        response = client.get("/api/v1/i18n/locales")
        for item in response.json():
            assert "name" in item
            assert len(item["name"]) > 0

    def test_locales_structure(self, client: TestClient) -> None:
        """Each locale item has exactly 'code' and 'name' keys."""
        response = client.get("/api/v1/i18n/locales")
        for item in response.json():
            assert set(item.keys()) == {"code", "name"}


class TestI18nAPITranslations:
    """Tests for GET /api/v1/i18n/translations/{locale}."""

    @pytest.mark.parametrize("locale", ["ca", "es", "en", "pl"])
    def test_translations_by_locale(self, client: TestClient, locale: str) -> None:
        """Translation endpoint returns non-empty dict for each locale."""
        response = client.get(f"/api/v1/i18n/translations/{locale}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 10

    def test_unknown_locale_fallback(self, client: TestClient) -> None:
        """Unknown locale returns default (Catalan) translations."""
        response = client.get("/api/v1/i18n/translations/xx")
        assert response.status_code == 200
        data = response.json()
        assert data["pdf.generated_at"] == "Generat el"

    def test_english_content(self, client: TestClient) -> None:
        """English translations contain expected English strings."""
        response = client.get("/api/v1/i18n/translations/en")
        data = response.json()
        assert data["pdf.generated_at"] == "Generated at"
        assert data["pdf.panels_section"] == "Dashboard Panels"
        assert data["status.completed"] == "Completed"

    def test_polish_content(self, client: TestClient) -> None:
        """Polish translations contain expected Polish strings."""
        response = client.get("/api/v1/i18n/translations/pl")
        data = response.json()
        assert data["pdf.generated_at"] == "Wygenerowano"
        assert data["status.completed"] == "Ukończony"
