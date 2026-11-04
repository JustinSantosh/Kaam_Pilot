"""How backend/.env reaches the app: Settings reads KP_* itself, and only the other keys (provider
keys, tracing) are copied into os.environ for the SDKs that read them from there."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.config import Settings, get_settings

pytestmark = pytest.mark.usefixtures("dotenv_file")


@pytest.fixture
def dotenv_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """A throwaway .env in the working directory, read by a fresh `get_settings()`."""
    (tmp_path / ".env").write_text(
        "KP_FOLLOWUP_HOURS=0.01\nGOOGLE_API_KEY=from-dotenv\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    for name in ("KP_FOLLOWUP_HOURS", "GOOGLE_API_KEY"):
        monkeypatch.setenv(name, "")  # recorded first, so it's restored even if the app sets it
        monkeypatch.delenv(name)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_dotenv_configures_the_app() -> None:
    assert get_settings().followup_hours == 0.01


def test_dotenv_stays_out_of_settings_that_opt_out() -> None:
    get_settings()
    assert "KP_FOLLOWUP_HOURS" not in os.environ
    assert Settings(_env_file=None).followup_hours == 48.0


def test_dotenv_exports_provider_keys_for_the_sdks() -> None:
    get_settings()
    assert os.environ["GOOGLE_API_KEY"] == "from-dotenv"


def test_real_environment_wins_over_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KP_FOLLOWUP_HOURS", "5")
    monkeypatch.setenv("GOOGLE_API_KEY", "from-shell")
    assert get_settings().followup_hours == 5.0
    assert os.environ["GOOGLE_API_KEY"] == "from-shell"


def test_test_runs_never_send_traces() -> None:
    assert os.environ["LANGSMITH_TRACING"] == "false"
