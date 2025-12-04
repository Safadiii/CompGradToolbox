from fastapi import APIRouter, HTTPException
from app.services.ta_services import get_all_tas, get_ta_by_id

router = APIRouter()

@router.get("/tas")
def fetch_all_tas():
    """
    Return all TAs from the database.
    """
    try:
        tas = get_all_tas()
        return tas
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/tas/{ta_id}")
def fetch_ta(ta_id: int):
    """
    Return a single TA by ID
    """
    try:
        ta = get_ta_by_id(ta_id)
        if not ta:
            raise HTTPException(status_code=404, detail="TA not found")
        return ta
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))