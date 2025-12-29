from fastapi import APIRouter, HTTPException
from app.services.skills_services import get_all_skills

router = APIRouter()

@router.get("/skills")
def fetch_skills():
    try:
        return get_all_skills()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
