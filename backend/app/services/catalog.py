from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError

from app.schemas.pricing import Catalog

DEFAULT_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "catalog.json"


class CatalogError(RuntimeError):
    pass


def load_catalog(path: Path = DEFAULT_CATALOG_PATH) -> Catalog:
    """Load and validate the catalog once per path. Raises CatalogError so startup fails fast."""
    return _load(path.resolve())


@lru_cache
def _load(path: Path) -> Catalog:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CatalogError(f"cannot read catalog at {path}: {exc}") from exc
    try:
        return Catalog.model_validate_json(raw)
    except ValidationError as exc:
        raise CatalogError(f"invalid catalog at {path}:\n{exc}") from exc
