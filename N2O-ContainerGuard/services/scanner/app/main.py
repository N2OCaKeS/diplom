from fastapi import FastAPI, HTTPException
from pathlib import Path
from .schemas import ImageScanRequest, ScanResult
from .trivy_adapter import run_trivy_image_scan
from .normalizer import normalize_trivy_json, summarize
from .storage import ensure_dirs, write_json, OUT_DIR

app = FastAPI(title="N2O Scanner (Trivy)")


@app.on_event("startup")
def startup():
    ensure_dirs()


@app.post("/scan/image", response_model=ScanResult)
def scan_image(req: ImageScanRequest):
    try:
        trivy_json, raw_path = run_trivy_image_scan(req.ref, OUT_DIR / "raw")
        findings = normalize_trivy_json(trivy_json)
        summary = summarize(findings)

        # сохраняем нормализованный отчёт
        normalized = {
            "artifact_type": "image",
            "ref": req.ref,
            "project": req.project,
            "policy_name": req.policy_name,
            "summary": summary,
            "findings": [f.model_dump() for f in findings],
        }
        norm_file = OUT_DIR / "normalized" / (Path(raw_path).stem + ".json")
        normalized_path = write_json(norm_file, normalized)

        return ScanResult(
            ref=req.ref,
            summary=summary,
            findings=findings,
            raw_path=raw_path,
            normalized_path=normalized_path,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
