from fastapi import APIRouter, HTTPException, Query
from app.services.ta_assignments_services import get_assignments_for_ta

router = APIRouter()

@router.get("/ta-assignments/by-ta")
def fetch_ta_assignments(ta_id: int = Query(...)):
    try:
        return get_assignments_for_ta(ta_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
