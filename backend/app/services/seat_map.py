"""Generates an invented seat map for a train run. DB doesn't publish real seat
maps, so this is deliberately made-up data -- 2 coaches, first class with 2-across
seating and second class with 4-across, priced flat per class.
"""

from app.models.train import Coach, Seat

FIRST_CLASS_ROWS = 8
FIRST_CLASS_LETTERS = "AB"
FIRST_CLASS_PRICE = 89.90

SECOND_CLASS_ROWS = 8
SECOND_CLASS_LETTERS = "ABCD"
SECOND_CLASS_PRICE = 49.90


def _build_coach(coach_number: int, seat_class: str, price: float, rows: int, letters: str) -> Coach:
    return Coach(
        coach_number=coach_number,
        seat_class=seat_class,
        price=price,
        seats=[Seat(seat_number=f"{row}{letter}") for row in range(1, rows + 1) for letter in letters],
    )


def build_coaches() -> list[Coach]:
    return [
        _build_coach(1, "first", FIRST_CLASS_PRICE, FIRST_CLASS_ROWS, FIRST_CLASS_LETTERS),
        _build_coach(2, "second", SECOND_CLASS_PRICE, SECOND_CLASS_ROWS, SECOND_CLASS_LETTERS),
    ]
