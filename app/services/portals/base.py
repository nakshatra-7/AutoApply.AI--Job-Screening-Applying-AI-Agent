from __future__ import annotations

from typing import List, Protocol

from app.schemas.discovery import DiscoveredField, FillAction


class PortalAdapter(Protocol):
    name: str

    def matches(self, url: str, html: str) -> bool:
        ...

    def discover_fields(self, url: str, html: str) -> List[DiscoveredField]:
        ...

    def build_fill_actions(
        self, fields: List[DiscoveredField], answers: dict[str, str]
    ) -> List[FillAction]:
        ...
