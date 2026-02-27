from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.database import get_db
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate, PatientResponse, PatientListResponse
from app.auth import get_current_user, UserPrincipal

router = APIRouter()


def _apply_role_restrictions(response: PatientResponse, user: UserPrincipal) -> PatientResponse:
    """Strip fields the current role is not permitted to see."""
    if not user.can_see_ssn:
        response.ssn = None
    return response


@router.get("", response_model=PatientListResponse)
async def list_patients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query("", description="Search by name, ID, or condition"),
    risk_level: str = Query("", description="Filter: high, medium, low"),
    db: AsyncSession = Depends(get_db),
    current_user: UserPrincipal = Depends(get_current_user),
):
    query = select(Patient)

    # Permission filter — admin sees all, others see assigned patients only
    allowed_ids = current_user.get_allowed_patient_ids()
    if allowed_ids is not None:
        query = query.where(Patient.patient_id.in_(allowed_ids))

    if search:
        query = query.where(
            or_(
                Patient.name.ilike(f"%{search}%"),
                Patient.patient_id.ilike(f"%{search}%"),
                Patient.conditions.cast(str).ilike(f"%{search}%"),
            )
        )

    if risk_level == "high":
        query = query.where(Patient.risk_score > 75)
    elif risk_level == "medium":
        query = query.where(Patient.risk_score.between(50, 75))
    elif risk_level == "low":
        query = query.where(Patient.risk_score < 50)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Paginate
    query = query.order_by(Patient.patient_id).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    patients = result.scalars().all()

    patient_responses = [
        _apply_role_restrictions(PatientResponse.model_validate(p), current_user)
        for p in patients
    ]

    return PatientListResponse(
        patients=patient_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserPrincipal = Depends(get_current_user),
):
    if not current_user.has_access_to_patient(patient_id):
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: {patient_id} is not in your assigned patients",
        )
    result = await db.execute(select(Patient).where(Patient.patient_id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    return _apply_role_restrictions(PatientResponse.model_validate(patient), current_user)


@router.post("", response_model=PatientResponse, status_code=201)
async def create_patient(
    data: PatientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserPrincipal = Depends(get_current_user),
):
    if not current_user.can_write:
        raise HTTPException(status_code=403, detail="Your role does not permit creating patients")

    # Generate next patient ID
    max_id_result = await db.scalar(select(func.max(Patient.id)))
    next_num = (max_id_result or 0) + 1
    patient_id = f"PT-{str(next_num).zfill(3)}"

    patient = Patient(patient_id=patient_id, **data.model_dump())
    db.add(patient)
    await db.flush()
    await db.refresh(patient)
    return PatientResponse.model_validate(patient)


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    data: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserPrincipal = Depends(get_current_user),
):
    if not current_user.can_write:
        raise HTTPException(status_code=403, detail="Your role does not permit updating patients")
    if not current_user.has_access_to_patient(patient_id):
        raise HTTPException(status_code=403, detail=f"Access denied: {patient_id} is not in your assigned patients")

    result = await db.execute(select(Patient).where(Patient.patient_id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(patient, key, value)

    await db.flush()
    await db.refresh(patient)
    return PatientResponse.model_validate(patient)


@router.delete("/{patient_id}")
async def delete_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserPrincipal = Depends(get_current_user),
):
    if not current_user.can_write:
        raise HTTPException(status_code=403, detail="Your role does not permit deleting patients")
    if not current_user.has_access_to_patient(patient_id):
        raise HTTPException(status_code=403, detail=f"Access denied: {patient_id} is not in your assigned patients")

    result = await db.execute(select(Patient).where(Patient.patient_id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

    await db.delete(patient)
    await db.flush()
    return {"deleted": True, "patient_id": patient_id}
