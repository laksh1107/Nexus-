import os
from celery import Celery
from .database import SessionLocal, engine, Base
from .models import Job, Incident
from .engine import analyse
redis=os.getenv("REDIS_URL","redis://localhost:6379/0")
celery_app=Celery("nexus",broker=redis,backend=redis)
celery_app.conf.update(task_serializer="json",result_serializer="json",accept_content=["json"],timezone="UTC",task_track_started=True)
@celery_app.task(name="nexus.analyse_job")
def analyse_job(job_id:int):
    Base.metadata.create_all(bind=engine)
    db=SessionLocal()
    try:
        job=db.get(Job,job_id)
        if not job:return
        job.status="processing";db.commit()
        result=analyse(job.raw_text,job.source)
        job.result=result;job.status="completed";job.total_logs=result["total_logs"];job.anomaly_count=result["anomaly_count"];job.incident_count=len(result["incidents"])
        for inc in result["incidents"]:
            db.add(Incident(job_id=job.id,title=inc["title"],severity=inc["severity"],root_service=inc["root_service"],confidence_score=inc["confidence_score"],evidence=inc,recommendation=inc["recommendation"]))
        db.commit()
    except Exception:
        db.rollback()
        job=db.get(Job,job_id)
        if job:job.status="failed";db.commit()
        raise
    finally:db.close()
