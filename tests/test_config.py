import pytest

from rapidocr_offline.config import AppSettings, load_settings


def test_load_settings_uses_environment_port(monkeypatch):
    monkeypatch.setenv("APP_HOST", "0.0.0.0")
    monkeypatch.setenv("APP_PORT", "9000")

    settings = load_settings()

    assert settings == AppSettings(host="0.0.0.0", port=9000)


def test_load_settings_rejects_invalid_port(monkeypatch):
    monkeypatch.setenv("APP_PORT", "70000")

    with pytest.raises(ValueError, match="APP_PORT"):
        load_settings()
