import re, json, os
from collections import Counter, defaultdict
from datetime import datetime
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import IsolationForest

def normalize(s):
    s=s.lower()
    s=re.sub(r'\b(?:[0-9a-f]{8,}|[0-9]{2,}|[0-9a-f]{2,}-[0-9a-f-]{8,})\b','<var>',s)
    s=re.sub(r'\b\d{1,3}(?:\.\d{1,3}){3}\b','<ip>',s)
    return re.sub(r'\s+',' ',s).strip()

def parse(line, i):
    ts=re.match(r'^(\d{4}-\d\d-\d\d[T ][0-9:.Z+-]+)\s+',line)
    level=re.search(r'\b(DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL|FATAL)\b',line,re.I)
    level=(level.group(1).upper() if level else ('ERROR' if re.search(r'failed|exception|error|fatal|timeout',line,re.I) else 'INFO'))
    svc=re.search(r'\b(api[-_ ]?gateway|database|postgres(?:ql)?|redis|auth(?:entication)?[-_ ]?service|order[-_ ]?service|payment[-_ ]?service|worker|kafka|nginx|hdfs|datanode|namenode|systemd|kernel)\b',line,re.I)
    service=(svc.group(1).lower().replace(' ','-') if svc else 'application')
    msg=line[ts.end():] if ts else line
    return {"event_id":i+1,"timestamp":ts.group(1) if ts else None,"level":level,"service":service,"message":msg[:1200],"template":normalize(msg)[:300]}

def drain_templates(lines):
    # Use Drain3 streaming parser if installed; retain regex fallback for reproducibility.
    try:
        from drain3 import TemplateMiner
        from drain3.template_miner_config import TemplateMinerConfig
        cfg=TemplateMinerConfig(); cfg.drain_sim_th=0.45; cfg.drain_max_depth=4
        miner=TemplateMiner(config=cfg)
        output=[]
        for line in lines:
            res=miner.add_log_message(line)
            output.append(res.get("template_mined",normalize(line)))
        return output,"Drain3"
    except Exception:
        return [normalize(x) for x in lines],"Regex normalization fallback"

def analyse(text, dataset="custom"):
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    parsed=[parse(line,i) for i,line in enumerate(lines)]
    templates,parser=drain_templates(lines)
    for row,t in zip(parsed,templates): row["template"]=t
    # Unsupervised text model. On tiny inputs the robust signature rules remain active.
    messages=[x["template"] for x in parsed]
    scores=np.zeros(len(messages)); model_status="rules-only (too few distinct messages)"
    if len(messages)>=12 and len(set(messages))>=4:
        try:
            vec=TfidfVectorizer(max_features=2500,ngram_range=(1,2),min_df=1,sublinear_tf=True)
            X=vec.fit_transform(messages)
            model=IsolationForest(n_estimators=150,contamination="auto",random_state=42,n_jobs=-1)
            model.fit(X)
            scores=-model.decision_function(X)
            model_status="TF-IDF + Isolation Forest (unsupervised, fitted per analysis)"
        except Exception as e: model_status="rules-only fallback: "+str(e)[:120]
    # combine model score with severity and known failure signatures
    severity={"ERROR":0.35,"CRITICAL":0.55,"FATAL":0.55,"WARN":0.08,"WARNING":0.08}
    rules=[
      (r'outofmemory|heap space|memory pressure|oomkilled|exit.?code.?137','Memory exhaustion','memory'),
      (r'too many connections|pool exhausted|connection refused|could not connect|database.*timeout','Database connection / pool exhaustion','database'),
      (r'missing.*environment|not set|configuration.*missing|no such file or directory','Missing configuration / deployment failure','configuration'),
      (r'dns.*fail|name or service not known|network unreachable|connection timed out','Network / DNS connectivity failure','network'),
      (r'http.?5\d\d|upstream.*unavailable|upstream timeout','Downstream HTTP 5xx symptom','downstream'),
      (r'permission denied|unauthorized|authentication failed|invalid token','Permission / authentication failure','security')
    ]
    candidates=[]
    for idx,row in enumerate(parsed):
        row["anomaly_score"]=round(float(scores[idx]),5)
        row["is_anomaly"]=False
        row["reason"]=""
        if row["level"] in ("ERROR","CRITICAL","FATAL"):
            row["is_anomaly"]=True; row["reason"]="Error severity"
        for pat,label,key in rules:
            if re.search(pat,row["message"],re.I):
                row["is_anomaly"]=True; row["reason"]=label
                candidates.append((idx,key,label,row)); break
        if len(messages)>=12 and scores[idx] > np.quantile(scores,0.90):
            row["is_anomaly"]=True
            if not row["reason"]: row["reason"]="Unusual TF-IDF log pattern (Isolation Forest)"
    priority={"memory":0,"database":0,"configuration":0,"network":0,"security":1,"downstream":3}
    candidates.sort(key=lambda c:(priority.get(c[1],2),c[0]))
    anomalies=[x for x in parsed if x["is_anomaly"]]
    incident=None
    if anomalies:
        root=candidates[0] if candidates else (0,"unknown","Unclassified anomalous log",anomalies[0])
        idx,key,label,row=root
        services=list(dict.fromkeys(x["service"] for x in anomalies))
        sev="CRITICAL" if sum(x["level"] in ("ERROR","CRITICAL","FATAL") for x in anomalies)>=4 else "HIGH"
        rec={
          "memory":"Inspect container memory/heap, recent workload and OOMKilled events. Capture diagnostics before changing limits.",
          "database":"Inspect active sessions, pool saturation, leaked connections and slow queries; verify database and dependent service health.",
          "configuration":"Validate required environment variables, mounted secrets and configuration maps; compare the latest deployment.",
          "network":"Check DNS, service discovery, network policies and upstream reachability from the affected container.",
          "security":"Review credential rotation, token issuer, permissions and recent authentication configuration changes.",
          "downstream":"Inspect the upstream dependency before restarting the gateway.",
          "unknown":"Inspect the earliest anomalous event and correlate it with metrics, traces and deployment changes."
        }.get(key,"Inspect the earliest event and its dependencies.")
        incident={"title":label,"severity":sev,"root_service":row["service"],"root_event":row,"confidence_score":min(0.96,0.55+min(0.25,len(anomalies)*0.025)+(0.12 if key in priority else 0)),"affected_services":services,"anomaly_count":len(anomalies),"evidence":anomalies[:30],"recommendation":rec,"cause_key":key}
    return {"dataset":dataset,"parser":parser,"model":model_status,"total_logs":len(parsed),"anomaly_count":len(anomalies),"normal_count":len(parsed)-len(anomalies),"services":len(set(x["service"] for x in parsed)),"logs":parsed,"incidents":[incident] if incident else [],"templates":[{"template":k,"count":v} for k,v in Counter(x["template"] for x in parsed).most_common(12)],"severity":dict(Counter(x["level"] for x in parsed))}

def demo_logs(kind="database"):
    cases={
    "database":[
    "2026-11-18T10:00:00Z INFO api-gateway GET /health 200 latency=12ms",
    "2026-11-18T10:00:03Z INFO auth-service token validated",
    "2026-11-18T10:01:10Z WARN database connection pool usage=92%",
    "2026-11-18T10:01:14Z ERROR database too many connections pool exhausted max=100",
    "2026-11-18T10:01:16Z ERROR order-service could not connect to database timeout=3000ms",
    "2026-11-18T10:01:18Z ERROR api-gateway upstream order-service returned HTTP 500",
    "2026-11-18T10:01:20Z ERROR api-gateway upstream order-service returned HTTP 500",
    "2026-11-18T10:01:22Z ERROR api-gateway upstream order-service returned HTTP 500",
    "2026-11-18T10:01:25Z ERROR order-service could not connect to database timeout=3000ms",
    "2026-11-18T10:01:29Z ERROR database connection refused host=db-primary",
    "2026-11-18T10:02:01Z WARN api-gateway elevated error rate route=/orders"],
    "memory":[
    "2026-11-18T11:20:00Z INFO worker-job started queue=thumbnail",
    "2026-11-18T11:20:05Z INFO image-worker processing batch=120",
    "2026-11-18T11:20:10Z WARN image-worker memory usage=78%",
    "2026-11-18T11:20:15Z WARN image-worker memory usage=96%",
    "2026-11-18T11:20:18Z ERROR image-worker Java heap space allocation failed",
    "2026-11-18T11:20:19Z ERROR image-worker OutOfMemoryError Java heap space",
    "2026-11-18T11:20:20Z ERROR image-worker container killed exit_code=137",
    "2026-11-18T11:20:22Z ERROR queue-consumer worker unavailable retrying",
    "2026-11-18T11:20:25Z ERROR api-gateway upstream timeout route=/images"],
    "configuration":[
    "2026-11-18T12:40:00Z INFO deployment release=v2.8.1 started",
    "2026-11-18T12:40:03Z INFO config-service loading environment",
    "2026-11-18T12:40:05Z ERROR config-service missing required environment variable DATABASE_URL",
    "2026-11-18T12:40:06Z ERROR payment-service startup failed DATABASE_URL is not set",
    "2026-11-18T12:40:07Z ERROR payment-service health check failed status=503",
    "2026-11-18T12:40:09Z ERROR api-gateway upstream payment-service unavailable",
    "2026-11-18T12:40:12Z ERROR api-gateway HTTP 503 route=/checkout"]
    }
    return "\n".join(cases.get(kind,cases["database"]))
