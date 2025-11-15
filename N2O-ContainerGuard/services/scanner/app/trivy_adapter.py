from pathlib import Path
from typing import Dict, Any  
import uuid
import subprocess
import json

TRIVY_IMAGE = "aquasec/trivy:0.50.2"

def run_trivy_image_scan(ref: str, workdir: Path) -> tuple[Dict[str, Any], str]:
    """
    Возвращает (trivy_json, raw_path).
    """
    raw_path = workdir / f"{uuid.uuid4()}.json"

    cmd = [
        "docker", "run", "--rm",
        "-v", "/var/run/docker.sock:/var/run/docker.sock",
        TRIVY_IMAGE, "image",
        "--format", "json",
        "--quiet",
        ref
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode not in (0, 5):
        raise RuntimeError(f"trivy failed ({proc.returncode}): {proc.stderr}")

    raw = proc.stdout
    raw_path.write_text(raw)
    data: Dict[str, Any] = json.loads(raw)
    return data, str(raw_path.resolve())
