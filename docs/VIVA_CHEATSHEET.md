# NEXUS viva cheat sheet

**Problem:** Distributed applications produce many logs; manual investigation is slow and symptoms can be mistaken for causes.

**Input:** Uploaded .log/.txt/.csv records or repeatable fault scenarios.

**Pipeline:** parse → normalize/template mine → TF-IDF vectors → Isolation Forest score + severity/signature rules → service/time evidence aggregation → ranked RCA hypothesis → optional Gemini explanation.

**Model:** TF-IDF + Isolation Forest, unsupervised per uploaded batch. Drain3 is the streaming parser, not the ML classifier. Gemini is an optional explanation model, not the anomaly detector.

**Dataset:** Synthetic scenarios for controlled demonstration; LogHub HDFS_v1 and BGL are public benchmark datasets available via the downloader. Synthetic demo performance must not be reported as benchmark accuracy.

**Cloud/DevOps:** Docker Compose runs frontend, FastAPI API, PostgreSQL, Redis, Celery worker, Loki, Promtail, Prometheus and Grafana. Kubernetes manifests demonstrate Deployments/Services. Terraform uses local Docker provider. GitHub Actions runs tests/build.

**Limitations:** The RCA engine is heuristic and log-only; no distributed tracing/metrics fusion yet. Isolation Forest is a baseline and fitted per batch. Benchmark evaluation must use trace/block-aware splits to prevent data leakage.
