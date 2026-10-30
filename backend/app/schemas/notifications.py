# OWNER: P2
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class NotificationDraftSchema(BaseModel):
    id: str
    audience: str
    channel: str
    recipient: str
    subject: Optional[str] = None
    body: str
    status: str
    requires_approval: bool
    template_key: Optional[str] = None
    related_change_set_id: Optional[str] = None
    related_incident_id: Optional[str] = None
    created_at: str


class GenerateDraftsRequest(BaseModel):
    event_type: str
    change_set_id: Optional[str] = None
    incident_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class EditDraftRequest(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    channel: Optional[str] = None
    recipient: Optional[str] = None


class DeliveryLogSchema(BaseModel):
    id: str
    draft_id: str
    audience: str
    recipient: str
    channel: str
    subject: Optional[str] = None
    body: str
    sent_at: str
    status: str
    provider: str


class TemplateSchema(BaseModel):
    key: str
    audience: str
    channel: str
    title: str
    body_template: str
