from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.services.assignment_history_services import (
    save_assignment_run_from_db,
    list_assignment_runs,
    get_assignment_run,
    apply_run,
    delete_assignment_run
)
from app.services.activity_log_service import add_log
import traceback

router = APIRouter()

@router.post("/assignment-runs/save-current")
def save_current_assignments(user: Optional[str] = Query(None), notes: Optional[str] = Query(None)):
    try:
        run_id = save_assignment_run_from_db(created_by=user, notes=notes)
        return {"run_id": run_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/assignment-runs")
def fetch_runs(limit: int = 50):
    try:
        return list_assignment_runs(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/assignment-runs/{run_id}")
def fetch_run(run_id: int):
    try:
        data = get_assignment_run(run_id)
        if not data:
            raise HTTPException(status_code=404, detail="Run not found")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/assignment-runs/{run_id}/apply")
def apply_assignment(run_id: int, user: str = "System"):
    return apply_run(run_id)

@router.delete("/assignment-runs/{run_id}")
def delete_run(run_id: int, user: str = "System"):
    try:
        deleted = delete_assignment_run(run_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Run not found")

        add_log(
            action=f"Deleted assignment run #{run_id}",
            user=user,
            type="warning",
        )
        return {"ok": True, "run_id": run_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
