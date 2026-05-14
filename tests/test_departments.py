import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def make_dept(client: TestClient, name: str, parent_id: int | None = None) -> dict:
    payload = {"name": name}
    if parent_id is not None:
        payload["parent_id"] = parent_id
    resp = client.post("/departments/", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def make_employee(client: TestClient, dept_id: int, full_name: str = "John Doe", position: str = "Engineer") -> dict:
    resp = client.post(f"/departments/{dept_id}/employees/", json={"full_name": full_name, "position": position})
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# POST /departments/
# ---------------------------------------------------------------------------

class TestCreateDepartment:
    def test_success_root(self, client):
        data = make_dept(client, "Engineering")
        assert data["name"] == "Engineering"
        assert data["parent_id"] is None
        assert "id" in data

    def test_success_with_parent(self, client):
        parent = make_dept(client, "IT")
        child = make_dept(client, "Backend", parent_id=parent["id"])
        assert child["parent_id"] == parent["id"]

    def test_name_stripped(self, client):
        data = make_dept(client, "  IT  ")
        assert data["name"] == "IT"

    def test_empty_name_rejected(self, client):
        resp = client.post("/departments/", json={"name": "   "})
        assert resp.status_code == 422

    def test_name_too_long_rejected(self, client):
        resp = client.post("/departments/", json={"name": "A" * 201})
        assert resp.status_code == 422

    def test_duplicate_name_same_parent_rejected(self, client):
        make_dept(client, "Backend")
        resp = client.post("/departments/", json={"name": "Backend"})
        assert resp.status_code == 409

    def test_same_name_different_parents_allowed(self, client):
        p1 = make_dept(client, "Russia")
        p2 = make_dept(client, "Germany")
        make_dept(client, "IT", parent_id=p1["id"])
        resp = client.post("/departments/", json={"name": "IT", "parent_id": p2["id"]})
        assert resp.status_code == 201

    def test_parent_not_found(self, client):
        resp = client.post("/departments/", json={"name": "IT", "parent_id": 9999})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /departments/{id}
# ---------------------------------------------------------------------------

class TestGetDepartment:
    def test_success(self, client):
        dept = make_dept(client, "IT")
        resp = client.get(f"/departments/{dept['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == dept["id"]
        assert data["employees"] == []
        assert data["children"] == []

    def test_not_found(self, client):
        assert client.get("/departments/9999").status_code == 404

    def test_children_visible_at_depth_2(self, client):
        parent = make_dept(client, "IT")
        make_dept(client, "Backend", parent_id=parent["id"])
        data = client.get(f"/departments/{parent['id']}?depth=2").json()
        assert len(data["children"]) == 1
        assert data["children"][0]["name"] == "Backend"

    def test_children_hidden_at_depth_1(self, client):
        parent = make_dept(client, "IT")
        child = make_dept(client, "Backend", parent_id=parent["id"])
        make_dept(client, "QA", parent_id=child["id"])
        data = client.get(f"/departments/{parent['id']}?depth=1").json()
        assert len(data["children"]) == 1
        assert data["children"][0]["children"] == []

    def test_depth_max_5(self, client):
        resp = client.get("/departments/1?depth=6")
        assert resp.status_code == 422

    def test_include_employees_false(self, client):
        dept = make_dept(client, "IT")
        make_employee(client, dept["id"])
        data = client.get(f"/departments/{dept['id']}?include_employees=false").json()
        assert data["employees"] == []

    def test_employees_sorted_by_full_name(self, client):
        dept = make_dept(client, "IT")
        make_employee(client, dept["id"], full_name="Zara Smith")
        make_employee(client, dept["id"], full_name="Alice Brown")
        data = client.get(f"/departments/{dept['id']}?sort_by=full_name").json()
        names = [e["full_name"] for e in data["employees"]]
        assert names == sorted(names)


# ---------------------------------------------------------------------------
# PATCH /departments/{id}
# ---------------------------------------------------------------------------

class TestUpdateDepartment:
    def test_rename(self, client):
        dept = make_dept(client, "Old")
        resp = client.patch(f"/departments/{dept['id']}", json={"name": "New"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New"

    def test_move_to_parent(self, client):
        parent = make_dept(client, "IT")
        child = make_dept(client, "Backend")
        resp = client.patch(f"/departments/{child['id']}", json={"parent_id": parent["id"]})
        assert resp.status_code == 200
        assert resp.json()["parent_id"] == parent["id"]

    def test_move_to_root(self, client):
        parent = make_dept(client, "IT")
        child = make_dept(client, "Backend", parent_id=parent["id"])
        resp = client.patch(f"/departments/{child['id']}", json={"parent_id": None})
        assert resp.status_code == 200
        assert resp.json()["parent_id"] is None

    def test_self_parent_rejected(self, client):
        dept = make_dept(client, "IT")
        resp = client.patch(f"/departments/{dept['id']}", json={"parent_id": dept["id"]})
        assert resp.status_code == 409

    def test_cycle_rejected(self, client):
        parent = make_dept(client, "IT")
        child = make_dept(client, "Backend", parent_id=parent["id"])
        resp = client.patch(f"/departments/{parent['id']}", json={"parent_id": child["id"]})
        assert resp.status_code == 409

    def test_duplicate_name_in_parent_rejected(self, client):
        make_dept(client, "Backend")
        dept2 = make_dept(client, "Frontend")
        resp = client.patch(f"/departments/{dept2['id']}", json={"name": "Backend"})
        assert resp.status_code == 409

    def test_not_found(self, client):
        assert client.patch("/departments/9999", json={"name": "X"}).status_code == 404


# ---------------------------------------------------------------------------
# DELETE /departments/{id}
# ---------------------------------------------------------------------------

class TestDeleteDepartment:
    def test_cascade_deletes_children(self, client):
        parent = make_dept(client, "IT")
        child = make_dept(client, "Backend", parent_id=parent["id"])
        resp = client.delete(f"/departments/{parent['id']}?mode=cascade")
        assert resp.status_code == 204
        assert client.get(f"/departments/{child['id']}").status_code == 404

    def test_cascade_deletes_employees(self, client):
        dept = make_dept(client, "IT")
        emp = make_employee(client, dept["id"])
        client.delete(f"/departments/{dept['id']}?mode=cascade")
        data = client.get(f"/departments/{dept['id']}")
        assert data.status_code == 404

    def test_reassign_moves_employees(self, client):
        source = make_dept(client, "Source")
        target = make_dept(client, "Target")
        make_employee(client, source["id"], full_name="Alice")
        resp = client.delete(
            f"/departments/{source['id']}?mode=reassign&reassign_to_department_id={target['id']}"
        )
        assert resp.status_code == 204
        target_data = client.get(f"/departments/{target['id']}").json()
        assert len(target_data["employees"]) == 1
        assert target_data["employees"][0]["full_name"] == "Alice"

    def test_reassign_promotes_children(self, client):
        parent = make_dept(client, "IT")
        child = make_dept(client, "Backend", parent_id=parent["id"])
        target = make_dept(client, "Other")
        client.delete(
            f"/departments/{parent['id']}?mode=reassign&reassign_to_department_id={target['id']}"
        )
        data = client.get(f"/departments/{child['id']}").json()
        assert data["parent_id"] is None

    def test_reassign_requires_target_id(self, client):
        dept = make_dept(client, "IT")
        resp = client.delete(f"/departments/{dept['id']}?mode=reassign")
        assert resp.status_code == 422

    def test_not_found(self, client):
        assert client.delete("/departments/9999?mode=cascade").status_code == 404


# ---------------------------------------------------------------------------
# POST /departments/{id}/employees/
# ---------------------------------------------------------------------------

class TestCreateEmployee:
    def test_success(self, client):
        dept = make_dept(client, "IT")
        resp = client.post(
            f"/departments/{dept['id']}/employees/",
            json={"full_name": "Alice Brown", "position": "Developer"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["full_name"] == "Alice Brown"
        assert data["department_id"] == dept["id"]

    def test_fields_stripped(self, client):
        dept = make_dept(client, "IT")
        resp = client.post(
            f"/departments/{dept['id']}/employees/",
            json={"full_name": "  Alice  ", "position": "  Dev  "},
        )
        data = resp.json()
        assert data["full_name"] == "Alice"
        assert data["position"] == "Dev"

    def test_department_not_found(self, client):
        resp = client.post(
            "/departments/9999/employees/",
            json={"full_name": "Alice", "position": "Dev"},
        )
        assert resp.status_code == 404

    def test_empty_full_name_rejected(self, client):
        dept = make_dept(client, "IT")
        resp = client.post(
            f"/departments/{dept['id']}/employees/",
            json={"full_name": "  ", "position": "Dev"},
        )
        assert resp.status_code == 422

    def test_name_too_long_rejected(self, client):
        dept = make_dept(client, "IT")
        resp = client.post(
            f"/departments/{dept['id']}/employees/",
            json={"full_name": "A" * 201, "position": "Dev"},
        )
        assert resp.status_code == 422

    def test_hired_at_optional(self, client):
        dept = make_dept(client, "IT")
        resp = client.post(
            f"/departments/{dept['id']}/employees/",
            json={"full_name": "Alice", "position": "Dev", "hired_at": "2024-01-15"},
        )
        assert resp.status_code == 201
        assert resp.json()["hired_at"] == "2024-01-15"
