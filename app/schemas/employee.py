from datetime import datetime, date

from pydantic import BaseModel, Field, field_validator


class EmployeeCreate(BaseModel):
    full_name: str = Field(max_length=200)
    position: str = Field(max_length=200)
    hired_at: date | None = None

    @field_validator("full_name", "position")
    @classmethod
    def not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Поле не может быть пустым")
        return v


class EmployeeResponse(BaseModel):
    id: int
    department_id: int
    full_name: str
    position: str
    hired_at: date | None
    created_at: datetime

    model_config = {"from_attributes": True}
