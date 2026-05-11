from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    event_type: Literal['wedding', 'corporate', 'birthday']
    budget: int = Field(..., ge=50000, le=50000000)
    city: str = Field(..., min_length=2)
    preferences: str = Field(default='balanced, indoor')
    question: str = Field(default='Best planning strategy for this event')


class KnowledgeRequest(BaseModel):
    question: str
    event_type: Optional[str] = None
