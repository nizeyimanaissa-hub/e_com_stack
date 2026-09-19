from pydantic import BaseModel, ConfigDict


class StationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    eva_id: int
    name: str
    ds100: str | None
    lat: float | None
    lon: float | None
    federal_state: str | None
