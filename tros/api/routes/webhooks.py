import datetime

from fastapi import APIRouter, Depends

from tros.api.deps import get_execution_manager
from tros.api.execution_manager import ExecutionManager

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

@router.post("/simulate")
async def simulate_webhook(
    manager: ExecutionManager = Depends(get_execution_manager),
):
    """Simulate an airline flight cancellation webhook.
    Automatically starts a recovery mission in the background.
    """
    # Create a mock mission request for KUL -> SIN
    req_dict = {
        "origin": "KUL",
        "destination": "SIN",
        "departure_date": (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        "traveler_count": 1,
        "currency": "USD",
        "traveler_type": "Business",
        "disruption_type": "FlightCancelled",
        "budget_limit": 1000.0,
    }

    # Submit to execution manager
    execution = manager.submit(req_dict)

    return {
        "status": "success",
        "message": "Flight cancellation received. Recovery mission started.",
        "mission_id": execution.mission_id
    }
