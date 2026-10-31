from pathlib import Path

import pytest

from app.config import get_settings
from scripts.seed_demo import seed


async def test_seed_creates_every_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KP_STORAGE_DIR", str(tmp_path / "seed"))
    get_settings.cache_clear()
    try:
        out = await seed()
        assert out == {
            "Ravi (awaiting approval)": "awaiting_approval",
            "Asha (sent, follow-up scheduled)": "sent",
            "Imran (needs clarification)": "needs_clarification",
            "Meera (edited to revision 2, awaiting)": "awaiting_approval",
            "Karan (accepted)": "accepted",
            "Sunil (injection refused)": "refused",
        }
        assert await seed() == {}  # second run is a no-op without --force
    finally:
        get_settings.cache_clear()
