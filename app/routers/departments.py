from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.department import Department
from app.models.employee import Employee
from app.schemas.department import DepartmentCreate, DepartmentResponse
from app.schemas.employee import EmployeeCreate, EmployeeResponse

router = APIRouter(prefix="/departments", tags=["departments"])


@router.post("/", response_model=DepartmentResponse, status_code=201)
def create_department(body: DepartmentCreate, db: Session = Depends(get_db)):
    if body.parent_id is not None:
        parent = db.get(Department, body.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Родительское подразделение не найдено")

    department = Department(name=body.name, parent_id=body.parent_id)
    db.add(department)
    db.commit()
    db.refresh(department)
    return department


@router.post("/{department_id}/employees/", response_model=EmployeeResponse, status_code=201)
def create_employee(department_id: int, body: EmployeeCreate, db: Session = Depends(get_db)):
    department = db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Подразделение не найдено")

    employee = Employee(
        department_id=department_id,
        full_name=body.full_name,
        position=body.position,
        hired_at=body.hired_at,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee
