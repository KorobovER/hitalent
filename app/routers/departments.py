from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.department import Department
from app.models.employee import Employee
from app.schemas.department import DepartmentCreate, DepartmentResponse, DepartmentDetail
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


def _build_node(
    dept: Department,
    current_depth: int,
    max_depth: int,
    include_employees: bool,
    sort_by: str,
    db: Session,
) -> dict:
    employees = []
    if include_employees:
        order_col = Employee.full_name if sort_by == "full_name" else Employee.created_at
        employees = (
            db.query(Employee)
            .filter(Employee.department_id == dept.id)
            .order_by(order_col)
            .all()
        )

    children = []
    if current_depth < max_depth:
        child_depts = db.query(Department).filter(Department.parent_id == dept.id).all()
        children = [
            _build_node(c, current_depth + 1, max_depth, include_employees, sort_by, db)
            for c in child_depts
        ]

    return {
        "id": dept.id,
        "name": dept.name,
        "parent_id": dept.parent_id,
        "created_at": dept.created_at,
        "employees": employees,
        "children": children,
    }


@router.get("/{department_id}", response_model=DepartmentDetail)
def get_department(
    department_id: int,
    depth: int = Query(default=1, ge=1, le=5),
    include_employees: bool = Query(default=True),
    sort_by: Literal["full_name", "created_at"] = Query(default="full_name"),
    db: Session = Depends(get_db),
):
    dept = db.get(Department, department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Подразделение не найдено")

    return _build_node(dept, 1, depth, include_employees, sort_by, db)


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
