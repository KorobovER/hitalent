from datetime import datetime

from pydantic import BaseModel, field_validator

from app.schemas.employee import EmployeeResponse


class DepartmentCreate(BaseModel):
    name: str
    parent_id: int | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
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
