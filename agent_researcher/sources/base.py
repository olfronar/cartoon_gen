from __future__ import annotations

from typing import Protocol, runtime_checkable

from shared.models import RawItem


@runtime_checkable
class Source(Protocol):
    name: str

    def fetch(self) -> list[RawItem]:
        """Fetch raw items from this source. Return empty list on failure."""
        ...
