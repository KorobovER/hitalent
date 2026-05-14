from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.department import Department
from app.models.employee import Employee
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentResponse, DepartmentDetail
from app.schemas.employee import EmployeeCreate, EmployeeResponse

router = APIRouter(prefix="/departments", tags=["departments"])


def _check_name_unique(name: str, parent_id: int | None, db: Session, exclude_id: int | None = None) -> None:
    query = db.query(Department).filter(
        Department.name == name,
        Department.parent_id == parent_id,
    )
    if exclude_id is not None:
        query = query.filter(Department.id != exclude_id)
    if query.first():
        raise HTTPException(
            status_code=409,
            detail="Подразделение с таким именем уже существует в этом родительском подразделении",
        )


@router.post("/", response_model=DepartmentResponse, status_code=201)
def create_department(body: DepartmentCreate, db: Session = Depends(get_db)):
    if body.parent_id is not None:
        parent = db.get(Department, body.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Родительское подразделение не найдено")

    _check_name_unique(body.name, body.parent_id, db)

    department = Department(name=body.name, parent_id=body.parent_id)
    db.add(department)
    db.commit()
    db.refresh(department)
    return department


def _would_create_cycle(dept_id: int, new_parent_id: int, db: Session) -> bool:
    current_id: int | None = new_parent_id
    while current_id is not None:
        if current_id == dept_id:
            return True
        parent = db.get(Department, current_id)
        current_id = parent.parent_id if parent else None
    return False


@router.patch("/{department_id}", response_model=DepartmentResponse)
def update_department(department_id: int, body: DepartmentUpdate, db: Session = Depends(get_db)):
    dept = db.get(Department, department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Подразделение не найдено")

    if "name" in body.model_fields_set:
        if body.name is None:
            raise HTTPException(status_code=422, detail="name не может быть null")

    if "parent_id" in body.model_fields_set and body.parent_id is not None:
        new_parent_id = body.parent_id
        if new_parent_id == department_id:
            raise HTTPException(status_code=409, detail="Подразделение не может быть родителем самого себя")
        parent = db.get(Department, new_parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Родительское подразделение не найдено")
        if _would_create_cycle(department_id, new_parent_id, db):
            raise HTTPException(status_code=409, detail="Операция создаёт цикл в дереве подразделений")

    final_name = body.name if "name" in body.model_fields_set else dept.name
    final_parent_id = body.parent_id if "parent_id" in body.model_fields_set else dept.parent_id

    if "name" in body.model_fields_set or "parent_id" in body.model_fields_set:
        _check_name_unique(final_name, final_parent_id, db, exclude_id=department_id)

    dept.name = final_name
    dept.parent_id = final_parent_id

    db.commit()
    db.refresh(dept)
    return dept


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


@router.delete("/{department_id}", status_code=204)
def delete_department(
    department_id: int,
    mode: Literal["cascade", "reassign"] = Query(),
    reassign_to_department_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    dept = db.get(Department, department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Подразделение не найдено")

    if mode == "reassign":
        if reassign_to_department_id is None:
            raise HTTPException(
                status_code=422,
                detail="reassign_to_department_id обязателен при mode=reassign",
            )
        if reassign_to_department_id == department_id:
            raise HTTPException(
                status_code=400,
                detail="Нельзя перевести сотрудников в удаляемое подразделение",
            )
        target = db.get(Department, reassign_to_department_id)
        if not target:
            raise HTTPException(status_code=404, detail="Целевое подразделение не найдено")

        db.query(Employee).filter(Employee.department_id == department_id).update(
            {"department_id": reassign_to_department_id}
        )
        db.query(Department).filter(Department.parent_id == department_id).update(
            {"parent_id": dept.parent_id}
        )
        db.delete(dept)

    else:
        db.delete(dept)

    db.commit()


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
