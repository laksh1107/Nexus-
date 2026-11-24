import os, io, csv, json
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from .database import Base, engine, get_db
from .models import Job, Incident
from .engine import analyse, demo_logs
from .worker import analyse_job
app=FastAPI(title="NEXUS AIOps API",version="2.0.0",description="Evidence-first log anomaly detection and root-cause analysis")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:3002","http://127.0.0.1:3002"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
UPLOADS=Counter("nexus_analysis_submitted_total","Analysis jobs submitted",["source"])
@app.on_event("startup")
def startup(): Base.metadata.create_all(bind=engine)
def serialize_job(j):
    return {"id":j.id,"name":j.name,"source":j.source,"status":j.status,"total_logs":j.total_logs,"anomaly_count":j.anomaly_count,"incident_count":j.incident_count,"model_name":j.model_name,"created_at":j.created_at.isoformat() if j.created_at else None,"result":j.result or {}}
def create_job(db,text,name,source,background):
    job=Job(name=name,source=source,status="queued",raw_text=text)
    db.add(job);db.commit();db.refresh(job);UPLOADS.labels(source=source).inc()
    try: analyse_job.delay(job.id)
    except Exception:
        # local fallback if worker/Redis isn't running
        background.add_task(run_local,job.id)
    return serialize_job(job)
def run_local(job_id):
    from .worker import analyse_job as task
    task(job_id)
@app.get("/api/health")
def health():
    return {"status":"ok","service":"nexus-api","version":"2.0.0","model":"TF-IDF + Isolation Forest","queue":"Redis/Celery"}
@app.get("/metrics")
def metrics(): return StreamingResponse(iter([generate_latest()]),media_type=CONTENT_TYPE_LATEST)
@app.get("/api/jobs")
def jobs(db:Session=Depends(get_db)):
    return [serialize_job(x) for x in db.scalars(select(Job).order_by(desc(Job.id)).limit(50)).all()]
@app.get("/api/jobs/{job_id}")
def job_detail(job_id:int,db:Session=Depends(get_db)):
    j=db.get(Job,job_id)
    if not j:raise HTTPException(404,"Job not found")
    return serialize_job(j)
@app.post("/api/analyze")
async def upload_log(background:BackgroundTasks,file:UploadFile=File(...),db:Session=Depends(get_db)):
    if not file.filename.lower().endswith((".log",".txt",".csv")):raise HTTPException(415,"Upload a .log, .txt or .csv file")
    raw=await file.read()
    if len(raw)>25*1024*1024:raise HTTPException(413,"Maximum upload size is 25 MB")
    try:text=raw.decode("utf-8",errors="replace")
    except Exception:raise HTTPException(400,"Could not read uploaded file")
    if not text.strip():raise HTTPException(400,"The uploaded file is empty")
    return create_job(db,text,file.filename,"upload",background)
@app.post("/api/demo")
def demo(payload:dict,background:BackgroundTasks,db:Session=Depends(get_db)):
    kind=payload.get("scenario","database")
    if kind not in ("database","memory","configuration"):raise HTTPException(400,"Unknown demo scenario")
    return create_job(db,demo_logs(kind),f"Fault injection · {kind.title()}",f"demo:{kind}",background)
@app.get("/api/incidents")
def incidents(db:Session=Depends(get_db)):
    rows=db.scalars(select(Incident).order_by(desc(Incident.id)).limit(100)).all()
    return [{"id":x.id,"job_id":x.job_id,"title":x.title,"severity":x.severity,"root_service":x.root_service,"confidence_score":x.confidence_score,"recommendation":x.recommendation,"evidence":x.evidence,"created_at":x.created_at.isoformat() if x.created_at else None} for x in rows]
@app.get("/api/datasets")
def datasets():
    return [{"id":"demo","name":"NEXUS Microservice Fault Scenarios","type":"Built-in reproducible demo","size":"3 scenarios","labelled":True,"status":"ready"},{"id":"hdfs","name":"LogHub HDFS_v1","type":"Public benchmark","size":"11.17M lines · ~1.47 GiB","labelled":True,"status":"download via scripts/download_loghub.py"},{"id":"bgl","name":"LogHub BGL","type":"Public benchmark","size":"4.75M lines · ~709 MiB","labelled":True,"status":"download via scripts/download_loghub.py"}]
@app.get("/api/export/{job_id}")
def export(job_id:int,format:str="csv",db:Session=Depends(get_db)):
    j=db.get(Job,job_id)
    if not j:raise HTTPException(404,"Job not found")
    rows=(j.result or {}).get("logs",[])
    if format=="json":
        data=json.dumps(j.result,indent=2).encode()
        return StreamingResponse(io.BytesIO(data),media_type="application/json",headers={"Content-Disposition":f'attachment; filename="nexus-job-{job_id}.json"'})
    if format!="csv":raise HTTPException(400,"format must be csv or json")
    out=io.StringIO();w=csv.DictWriter(out,fieldnames=["event_id","timestamp","level","service","message","template","is_anomaly","anomaly_score","reason"]);w.writeheader()
    for r in rows:w.writerow({k:r.get(k) for k in w.fieldnames})
    data=io.BytesIO(out.getvalue().encode())
    return StreamingResponse(data,media_type="text/csv",headers={"Content-Disposition":f'attachment; filename="nexus-job-{job_id}.csv"'})
@app.post("/api/ai-explain")
async def ai_explain(payload:dict):
    key=os.getenv("GEMINI_API_KEY")
    if not key:raise HTTPException(400,"Gemini is optional. Set GEMINI_API_KEY in .env and restart Docker Compose.")
    import httpx
    model=os.getenv("GEMINI_MODEL","gemini-2.5-flash")
    evidence=payload.get("incident",{})
    prompt="Explain only this incident evidence. Return concise JSON: likely_root_cause, reasoning, next_steps. State uncertainty. Evidence: "+json.dumps(evidence)[:10000]
    async with httpx.AsyncClient(timeout=40) as client:
        r=await client.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",headers={"x-goog-api-key":key},json={"contents":[{"parts":[{"text":prompt}]}]})
    if r.status_code>=400:raise HTTPException(502,"Gemini request failed: "+r.text[:500])
    return {"text":r.json()["candidates"][0]["content"]["parts"][0]["text"],"model":model}
