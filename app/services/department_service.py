from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.employee import Employee


def check_name_unique(
    name: str,
    parent_id: int | None,
    db: Session,
    exclude_id: int | None = None,
) -> None:
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


def would_create_cycle(dept_id: int, new_parent_id: int, db: Session) -> bool:
    current_id: int | None = new_parent_id
    while current_id is not None:
        if current_id == dept_id:
            return True
        parent = db.get(Department, current_id)
        current_id = parent.parent_id if parent else None
    return False


def build_department_node(
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
            build_department_node(c, current_depth + 1, max_depth, include_employees, sort_by, db)
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
