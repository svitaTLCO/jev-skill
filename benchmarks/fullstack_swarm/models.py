from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class ScoreEntry(BaseModel):
    """Represents a player's score entry in a game."""
    player_name: str
    score: int
    wave: int


class TelemetryEvent(BaseModel):
    """Represents a telemetry event from the game."""
    event_type: str
    timestamp: float
    data: Dict[str, Any]