from __future__ import annotations

from typing import List

from app.schemas.discovery import DiscoveredField, FillAction
from app.services.portals.base import PortalAdapter
from app.services.portals.greenhouse import GreenhouseAdapter
from app.services.portals.lever import LeverAdapter
from app.services.portals.workday import WorkdayAdapter

adapters = [
    GreenhouseAdapter(),
    LeverAdapter(),
    WorkdayAdapter(),
]



class GenericAdapter:
    name = "generic"

    def matches(self, url: str, html: str) -> bool:
        return True

    def discover_fields(self, url: str, html: str) -> List[DiscoveredField]:
        return []

    def build_fill_actions(self, fields: List[DiscoveredField], answers: dict[str, str]) -> List[FillAction]:
        actions: List[FillAction] = []
        for field in fields:
            if field.field_id in answers:
                actions.append(
                    FillAction(
                        action_type="type",
                        field_id=field.field_id,
                        value=str(answers[field.field_id]),
                        confidence=0.5,
                        notes="Generic fallback mapping.",
                    )
                )
        return actions


adapters: List[PortalAdapter] = [
        GreenhouseAdapter(),
        LeverAdapter(),
        WorkdayAdapter(),
    ]


def pick_adapter(url: str, html: str) -> PortalAdapter:
    for adapter in adapters:
        if adapter.matches(url, html):
            return adapter
    return GenericAdapter()
