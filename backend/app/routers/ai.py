"""
app/routers/ai.py – Posture analysis and history query endpoints.
"""
from __future__ import annotations

import base64
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.pipeline import analyze_frame, PostureResult
from app.core.security import get_current_active_user
from app.database import get_db
from app.models.posture import PostureRecord
from app.models.user import User

router = APIRouter(prefix="/api/v1/ai", tags=["AI Pose"])

# UPLOADS CONFIGURATION
UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


class Base64AnalysisRequest(BaseModel):
    image: str  # Base64 data URI (e.g. "data:image/jpeg;base64,...")


class PostureRecordRead(BaseModel):
    id: int
    user_id: int
    posture_image: str
    posture_status: str
    disease_risk: str
    disease_probability: float
    created_at: datetime

    model_config = {"from_attributes": True}


class PostureStats(BaseModel):
    total_checks: int
    good_checks: int
    bad_checks: int
    health_score: float  # Percentage of GOOD posture checks
    disease_counts: dict[str, int]


# ── HELPER: Run Analysis and Save Record ──────────────────────────────────────
async def _process_and_save_frame(
    frame: np.ndarray,
    db: AsyncSession,
    user: User,
) -> PostureRecord:
    """
    Runs the posture model analysis on the given frame, saves the frame to disk
    as a unique file, records the outcome in the database, and returns the DB record.
    """
    # 1. Run inference
    result: PostureResult = analyze_frame(frame)
    if result.posture == "UNKNOWN" and result.error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"AI model inference failed: {result.error}",
        )

    # 2. Write the frame to the uploads directory as a JPG
    file_name = f"posture_{uuid.uuid4().hex[:12]}.jpg"
    file_path = UPLOADS_DIR / file_name
    
    # Save using OpenCV
    success = cv2.imwrite(str(file_path), frame)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save analyzed image frame to disk.",
        )

    # 3. Create the database record
    # Serve static path via /uploads/filename.jpg
    image_url = f"/uploads/{file_name}"
    
    db_record = PostureRecord(
        user_id=user.id,
        posture_image=image_url,
        posture_status=result.posture,
        disease_risk=result.disease or "None",
        disease_probability=result.confidence or 0.0,
    )
    
    db.add(db_record)
    await db.flush()
    await db.refresh(db_record)
    
    return db_record


# ── POST /analyze (Multipart Upload) ──────────────────────────────────────────
@router.post(
    "/analyze",
    response_model=PostureRecordRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an image file and analyze posture status",
)
async def analyze_image_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PostureRecord:
    # 1. Read file bytes
    try:
        contents = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read uploaded file: {exc}",
        )

    # 2. Decode image using OpenCV
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is not a valid image format.",
        )

    # 3. Process image frame
    return await _process_and_save_frame(frame, db, current_user)


# ── POST /analyze-base64 (Webcam Snapshot) ────────────────────────────────────
@router.post(
    "/analyze-base64",
    response_model=PostureRecordRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a base64 image data URI and analyze posture status",
)
async def analyze_image_base64(
    payload: Base64AnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PostureRecord:
    # 1. Strip base64 prefix
    b64_str = payload.image
    if "," in b64_str:
        b64_str = b64_str.split(",")[1]

    # 2. Decode base64
    try:
        img_bytes = base64.b64decode(b64_str)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 payload: {exc}",
        )

    # 3. Convert to numpy array and decode image
    nparr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to decode base64 string to image.",
        )

    # 4. Process frame
    return await _process_and_save_frame(frame, db, current_user)


# ── GET /history ──────────────────────────────────────────────────────────────
@router.get(
    "/history",
    response_model=List[PostureRecordRead],
    summary="Fetch the posture analysis history of the current user",
)
async def get_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[PostureRecord]:
    result = await db.execute(
        select(PostureRecord)
        .where(PostureRecord.user_id == current_user.id)
        .order_by(PostureRecord.created_at.desc())
    )
    return list(result.scalars().all())


# ── GET /stats ────────────────────────────────────────────────────────────────
@router.get(
    "/stats",
    response_model=PostureStats,
    summary="Get aggregated posture stats and chart data for the current user",
)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    # 1. Query general status counts
    total_res = await db.execute(
        select(func.count(PostureRecord.id))
        .where(PostureRecord.user_id == current_user.id)
    )
    total_checks = total_res.scalar() or 0

    good_res = await db.execute(
        select(func.count(PostureRecord.id))
        .where(PostureRecord.user_id == current_user.id)
        .where(PostureRecord.posture_status == "GOOD")
    )
    good_checks = good_res.scalar() or 0

    bad_checks = total_checks - good_checks

    # Health score is the percentage of GOOD posture checks
    health_score = (good_checks / total_checks * 100.0) if total_checks > 0 else 100.0

    # 2. Query disease distributions for BAD posture records
    disease_res = await db.execute(
        select(PostureRecord.disease_risk, func.count(PostureRecord.id))
        .where(PostureRecord.user_id == current_user.id)
        .where(PostureRecord.posture_status == "BAD")
        .group_by(PostureRecord.disease_risk)
    )
    
    # Initialize counts for known diseases
    disease_counts = {
        "Cervicalgie": 0,
        "Lombalgie": 0,
        "Radiculopathie": 0
    }
    
    for risk, count in disease_res.all():
        if risk in disease_counts:
            disease_counts[risk] = count
        else:
            # handle unexpected/unmapped risk strings gracefully
            disease_counts[risk] = count

    return {
        "total_checks": total_checks,
        "good_checks": good_checks,
        "bad_checks": bad_checks,
        "health_score": round(health_score, 1),
        "disease_counts": disease_counts,
    }
