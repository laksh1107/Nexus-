# Research and dataset foundations (2024–2026 focus)

## Recent papers used to shape the design

1. **Ali et al. (2025), “A comprehensive study of machine learning techniques for log-based anomaly detection,” Empirical Software Engineering.** DOI: 10.1007/s10664-025-10669-3. Used to motivate baseline comparison and evaluation with precision, recall and F1 rather than relying on accuracy alone.
2. **Tang et al. (2025), “MicroRCA-Agent: Microservice Root Cause Analysis Method Based on Large Language Model Agents,” arXiv:2509.15635.** Describes Drain parsing, Isolation Forest plus status-code signals, and staged LLM reasoning. NEXUS borrows the broad pipeline idea but implements a smaller deterministic RCA baseline.
3. **Pham et al. (2025), “RCAEval: A Benchmark for Root Cause Analysis of Microservice Systems with Telemetry Data,” WWW Companion 2025.** Introduces 735 failure cases across three systems and logs/metrics/traces. It motivates future multi-telemetry evaluation; this prototype currently ranks causes from logs only.
4. **Li et al. (2025), “System log anomaly detection based on contrastive learning and retrieval augmented,” Scientific Reports 15, 38370.** Motivates contextual/retrieval-oriented log analysis; NEXUS does not claim to reproduce its contrastive-learning model.
5. **“Anomaly detection and root-cause identification in microservices: a survey” (2026), Cluster Computing.** Surveyed microservice anomaly detection/RCA and reports datasets including AIOps Challenge, HDFS, TraceRCA, GAIA, MicroCU and SMD. Used to justify modular detector + RCA architecture.

## Datasets

### Built-in NEXUS fault scenarios
Three deterministic educational scenarios (database pool exhaustion, worker memory exhaustion, missing deployment configuration). These are synthetic logs created for repeatable demos, not a public benchmark and not suitable for publishing benchmark accuracy.

### LogHub HDFS_v1
Public, labelled Hadoop Distributed File System logs. LogHub reports 11,175,629 lines (~1.47 GiB) and block-level normal/anomaly labels. Download:
`python scripts/download_loghub.py --dataset HDFS`
HDFS_v1 includes HDFS_templates.csv, anomaly_label.csv, Event_traces.csv and related processed artifacts in the dataset archive. See https://github.com/logpai/loghub/tree/master/HDFS and https://github.com/logpai/loghub.

### LogHub BGL
Blue Gene/L supercomputer logs with alert-category tags. LogHub reports 4,747,963 lines (~708.76 MiB). Download:
`python scripts/download_loghub.py --dataset BGL`
See https://github.com/logpai/loghub/tree/master/BGL.

## Model and algorithm choices in this implementation

- **Drain3**: online log template mining, when installed. Regex normalization is an explicit fallback and is reported by the API.
- **TF-IDF + Isolation Forest**: unsupervised baseline fitted on the submitted log batch. It produces an anomaly score; explicit ERROR/CRITICAL/FATAL and high-signal failure signatures are also flagged. It is not a pretrained transformer and is not called LogBERT.
- **RCA ranking**: deterministic priority rules plus first occurrence, service and evidence aggregation. This is a ranked hypothesis, not causal proof or calibrated probability.
- **Gemini (optional)**: language generation for explanation only. The API key stays on the server; only selected incident evidence is sent after the user explicitly requests it.

## Required evaluation
Use a held-out split where possible. Report precision, recall, F1, false-positive rate and confusion matrix. Avoid random row splitting when multiple rows belong to the same trace/block; group by trace/block to prevent leakage. Compare at least: signature-only baseline, TF-IDF + Isolation Forest, and (as future work) LogBERT/DeepLog. Never report scores from synthetic demo logs as public-benchmark performance.

## Foundational citations
- Zhu et al. (2023), LogHub, IEEE ISSRE.
- Jiang et al. (2024), Loghub-2.0, ISSTA.
- Xu et al. (2009), HDFS console-log anomaly detection, SOSP.
- He et al. (2017), Drain, ICWS.
