from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JourneyLegOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mode: str
    origin_name: str
    destination_name: str
    departure: datetime
    arrival: datetime
    line_name: str | None
    operator: str | None


class JourneyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    legs: list[JourneyLegOut]
    departure: datetime
    arrival: datetime
    duration_minutes: int
    transfers: int
    price_amount: float | None
    price_currency: str | None
