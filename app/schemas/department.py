from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.employee import EmployeeResponse


class DepartmentCreate(BaseModel):
    name: str = Field(max_length=200)
    parent_id: int | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Имя нужно заполнить")
        return v


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    parent_id: int | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Имя нужно заполнить")
        return v


class DepartmentResponse(BaseModel):
    id: int
    name: str
    parent_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DepartmentDetail(BaseModel):
    id: int
    name: str
    parent_id: int | None
    created_at: datetime
    employees: list[EmployeeResponse]
    children: list["DepartmentDetail"]

    model_config = {"from_attributes": True}


DepartmentDetail.model_rebuild()
