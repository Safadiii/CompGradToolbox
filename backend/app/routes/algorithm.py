from fastapi import APIRouter, HTTPException
from app.services.assignmentAlgorithm import run_assignment_algorithm, updateDB
from app.services.activity_log_service import add_log
from app.services.assignment_history_services import save_assignment_run_from_db, save_run_items_from_active
import traceback

router = APIRouter()

@router.get("/run-assignment")
def run_assignment(user: str = "System"):
    """
    Run the TA assignment algorithm and return the assignments & workloads.
    """
    try:
        # Run algorithm
        result = run_assignment_algorithm()

        # Update DB with assignments
        updateDB(result["assignments"])
        run_id = save_assignment_run_from_db(created_by=user, notes="Algorithm run")
        save_run_items_from_active(run_id)



        # Log success
        add_log(
            action=f"TA assignment run completed (Run #{run_id})",            
            user=user,
            type="success"
        )

        return result

    except Exception as e:
        traceback.print_exc()   

        # Log failure
        add_log(
            action=f"TA assignment run failed: {str(e)}",
            user=user,
            type="warning"
        )

        raise HTTPException(status_code=500, detail=str(e))
