import pytest

from app.core.config import DEFAULT_CORS_ORIGINS, cors_origins


def test_default_origins_are_the_local_frontend(monkeypatch):
    monkeypatch.delenv("VERIFIGST_CORS_ORIGINS", raising=False)
    assert cors_origins() == list(DEFAULT_CORS_ORIGINS)


def test_origins_can_be_set_from_the_environment(monkeypatch):
    monkeypatch.setenv("VERIFIGST_CORS_ORIGINS", " https://a.example , https://b.example ,")
    assert cors_origins() == ["https://a.example", "https://b.example"]


def test_an_empty_setting_falls_back_to_the_defaults(monkeypatch):
    monkeypatch.setenv("VERIFIGST_CORS_ORIGINS", "  ")
    assert cors_origins() == list(DEFAULT_CORS_ORIGINS)


def test_a_wildcard_origin_is_refused(monkeypatch):
    monkeypatch.setenv("VERIFIGST_CORS_ORIGINS", "*")
    with pytest.raises(ValueError):
        cors_origins()
