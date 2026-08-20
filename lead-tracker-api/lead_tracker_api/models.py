"""Pydantic request/response models for the Lead Tracker API."""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LeadCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    company: Optional[str] = Field(None, max_length=200)
    budget: Optional[float] = Field(None, ge=0)
    source: Optional[str] = Field(None, max_length=100)


class Lead(LeadCreate):
    id: int
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "Lead":
        return cls(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            company=row["company"],
            budget=row["budget"],
            source=row["source"],
            created_at=row["created_at"],
        )


class LeadStats(BaseModel):
    total_leads: int
    high_value_leads: int
    avg_budget: float
