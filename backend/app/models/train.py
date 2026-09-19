import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Train(Base):
    __tablename__ = "trains"
    __table_args__ = (UniqueConstraint("category", "number", "departure"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    category: Mapped[str] = mapped_column(String)  # e.g. "ICE", "IC", "RE"
    number: Mapped[str] = mapped_column(String)
    operator: Mapped[str] = mapped_column(String)
    origin_eva: Mapped[int] = mapped_column(Integer)
    destination_eva: Mapped[int] = mapped_column(Integer)
    departure: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    arrival: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    coaches: Mapped[list["Coach"]] = relationship(back_populates="train", cascade="all, delete-orphan")


class Coach(Base):
    __tablename__ = "coaches"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    train_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trains.id", ondelete="CASCADE"))
    coach_number: Mapped[int] = mapped_column(Integer)
    seat_class: Mapped[str] = mapped_column(String)  # "first" | "second"
    price: Mapped[float] = mapped_column(Numeric(6, 2))

    train: Mapped["Train"] = relationship(back_populates="coaches")
    seats: Mapped[list["Seat"]] = relationship(back_populates="coach", cascade="all, delete-orphan")


class Seat(Base):
    __tablename__ = "seats"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    coach_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("coaches.id", ondelete="CASCADE"))
    seat_number: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="free")  # free | held | booked
    held_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    coach: Mapped["Coach"] = relationship(back_populates="seats")
