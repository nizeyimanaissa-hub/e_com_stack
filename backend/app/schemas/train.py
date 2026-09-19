import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TrainCreate(BaseModel):
    category: str
    number: str
    operator: str
    origin_eva: int
    destination_eva: int
    departure: datetime
    arrival: datetime


class RegisterTrainFromLegRequest(BaseModel):
    """What a client echoes back after picking one transit leg from a
    GET /api/v1/journeys result -- covers direct (transfers=0) journeys, where
    the leg's origin/destination are exactly the queried stations. A leg from a
    journey with transfers isn't supported yet (see README's Phase 3 notes)."""

    origin_eva: int
    destination_eva: int
    line_name: str  # e.g. "ICE 76" -- parsed into category + number
    operator: str | None = None
    departure: datetime
    arrival: datetime


class TrainOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    number: str
    operator: str
    origin_eva: int
    destination_eva: int
    departure: datetime
    arrival: datetime


class SeatOut(BaseModel):
    id: uuid.UUID
    coach_number: int
    seat_class: str
    seat_number: str
    price: float
    status: str
