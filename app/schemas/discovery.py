from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DiscoveredField(BaseModel):
    field_id: str
    label: str
    type: str
    required: bool
    options: List[str] = Field(default_factory=list)
    section: Optional[str] = None
    placeholder: Optional[str] = None
    raw_name: Optional[str] = None
    source_portal: Optional[str] = None


class FillAction(BaseModel):
    action_type: str
    field_id: str
    value: str
    confidence: float
    notes: Optional[str] = None


class DiscoveryResult(BaseModel):
    portal: str
    fields: List[DiscoveredField]
    page_url: str
    timestamp: datetime
