from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.analytics_service import analytics_service
from app.schemas.analytics import RiskCalculationRequest, TrendRequest, ReadmissionRequest

router = APIRouter()


@router.get("/risk-distribution")
async def risk_distribution(db: AsyncSession = Depends(get_db)):
    return await analytics_service.get_risk_distribution(db)


@router.get("/condition-prevalence")
async def condition_prevalence(db: AsyncSession = Depends(get_db)):
    return await analytics_service.get_condition_prevalence(db)


@router.post("/calculate-risk")
async def calculate_risk(req: RiskCalculationRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await analytics_service.calculate_risk(req.patient_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/trends")
async def analyze_trends(req: TrendRequest, db: AsyncSession = Depends(get_db)):
    return await analytics_service.analyze_trends(req.query, db)


@router.post("/predict-readmission")
async def predict_readmission(req: ReadmissionRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await analytics_service.predict_readmission(req.patient_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
