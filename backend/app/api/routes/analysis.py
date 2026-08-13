"""Routes : lancement et suivi des jobs d'analyse communale.

POST /api/municipalities/{insee}/analyze   lance le job (BackgroundTasks), retourne job_id
GET  /api/analysis-jobs/{job_id}           statut/progression
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.analysis import AnalysisJob
from app.models.enums import AnalysisJobStatusEnum
from app.models.municipality import Municipality
from app.schemas.analysis import AnalysisJobLaunched, AnalysisJobRead
from app.services.analysis_job import run_analysis_job

router = APIRouter(tags=["analysis"])


@router.post("/api/municipalities/{insee}/analyze", response_model=AnalysisJobLaunched)
def launch_analysis(insee: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> AnalysisJobLaunched:
    municipality = db.execute(select(Municipality).where(Municipality.insee_code == insee)).scalar_one_or_none()
    if municipality is None:
        municipality = Municipality(insee_code=insee, name=insee)
        db.add(municipality)
        db.commit()
        db.refresh(municipality)

    job = AnalysisJob(
        municipality_id=municipality.id,
        status=AnalysisJobStatusEnum.PENDING,
        progress_pct=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_analysis_job, job.id)

    return AnalysisJobLaunched(job_id=job.id, municipality_id=municipality.id, status=job.status.value)


@router.get("/api/analysis-jobs/{job_id}", response_model=AnalysisJobRead)
def get_analysis_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> AnalysisJob:
    job = db.get(AnalysisJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job d'analyse non trouve")
    return job
