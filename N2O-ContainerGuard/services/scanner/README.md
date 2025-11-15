# N2O Scanner (Trivy)

POST /scan/image
{
  "ref": "ghcr.io/org/app:tag",
  "project": "demo",
  "policy_name": "defaults"
}

Ответ: сводка по severity, список находок, пути к сырым и нормализованным отчётам в /data/out.
