from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Station(Base):
    __tablename__ = "stations"

    eva_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    ds100: Mapped[str | None] = mapped_column(String, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    federal_state: Mapped[str | None] = mapped_column(String, nullable=True)
