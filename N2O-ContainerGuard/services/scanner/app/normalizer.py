from typing import Dict, Any, List
from .schemas import Finding


def _pick_cvss(v: Dict[str, Any]) -> float | None:
    cvss = []
    for src in (v.get("CVSS") or {}).values():
        score = src.get("V3Score") or src.get("V2Score")
        if isinstance(score, (int, float)):
            cvss.append(float(score))
    return max(cvss) if cvss else None


def normalize_trivy_json(data: Dict[str, Any]) -> List[Finding]:
    findings: List[Finding] = []
    for res in data.get("Results", []):
        vulns = res.get("Vulnerabilities") or []
        for v in vulns:
            findings.append(
                Finding(
                    vuln_id=v.get("VulnerabilityID"),
                    title=v.get("Title"),
                    severity=(v.get("Severity") or "UNKNOWN").lower(),
                    package=v.get("PkgName"),
                    version=v.get("InstalledVersion"),
                    fixed_in=v.get("FixedVersion"),
                    cvss=_pick_cvss(v),
                    links=v.get("References") or [],
                    extra={
                        "target": res.get("Target"),
                        "class": res.get("Class"),
                        "type": res.get("Type"),
                    },
                )
            )
    return findings


def summarize(findings: List[Finding]) -> Dict[str, int]:
    summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0}
    for f in findings:
        summary[f.severity] = summary.get(f.severity, 0) + 1
    return summary
