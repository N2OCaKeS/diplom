from pathlib import Path
import json
from typing import Any

OUT_DIR = Path("/data/out")


def ensure_dirs() -> None:
    (OUT_DIR / "raw").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "normalized").mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return str(path)
