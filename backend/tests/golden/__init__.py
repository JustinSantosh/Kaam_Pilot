import json
from pathlib import Path

GOLDEN_PATH = Path(__file__).resolve().parent / "inquiries.json"


def load_golden() -> list[dict]:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
