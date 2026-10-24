"""Final price and duration of a master's service: ``COALESCE(override, base)``."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

__all__ = ["Offering"]


@dataclass(frozen=True, slots=True)
class Offering:
    """One service as one master offers it.

    Validated in the constructor. Money is ``Decimal``.
    """

    base_price: Decimal
    base_duration_min: int
    price_override: Decimal | None = None
    duration_override: int | None = None

    def __post_init__(self) -> None:
        if self.base_duration_min <= 0:
            raise ValueError("base duration has to be positive")
        if self.base_price < 0:
            raise ValueError("base price cannot be negative")
        if self.duration_override is not None and self.duration_override <= 0:
            raise ValueError("a duration override has to be positive")
        if self.price_override is not None and self.price_override < 0:
            raise ValueError("a price override cannot be negative")

    @property
    def price(self) -> Decimal:
        """What the client pays.

        A zero override is a real price (a service given away) and not an
        absent one, which is why this tests against ``None`` rather than
        against falsehood.
        """
        return self.base_price if self.price_override is None else self.price_override

    @property
    def duration_min(self) -> int:
        """How long the master is occupied, before the buffer.

        The buffer after a booking is configured in ``booking``.
        """
        return self.base_duration_min if self.duration_override is None else self.duration_override
