"""Mission Engine — creates and manages recovery missions (Arch §3.4).

The Mission Engine receives disruption events, creates missions,
initializes the Shared Mission State, and invokes the Supervisor.
"""

from __future__ import annotations

from tros.schemas.mission import (
    DisruptionEvent,
    MissionContext,
    MissionStatus,
    TravelerProfile,
    generate_mission_id,
)
from tros.state.mission_state import SharedMissionState


class MissionEngine:
    """Creates and manages recovery missions."""

    def create_mission(
        self,
        event: DisruptionEvent,
        departure_date: str,
        traveler: TravelerProfile | None = None,
        budget_limit: float = 1000.0,
    ) -> SharedMissionState:
        """Create a new recovery mission from a disruption event.

        Returns an initialized SharedMissionState in CREATED status.
        """
        mission_id = generate_mission_id()
        state = SharedMissionState(
            mission_id=mission_id,
            status=MissionStatus.CREATED,
            trigger_event=event.disruption_type.value,
        )
        state._append_audit("MissionEngine", "mission_created",
                            f"Mission {mission_id} created for {event.disruption_type.value}")
        return state
