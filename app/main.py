import logging

from fastapi import FastAPI

from app.routers import departments

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI(
    title="HiTalent API",
    version="1.0.0",
    description="API для управления подразделениями и сотрудниками компании.",
    openapi_tags=[
        {
            "name": "departments",
            "description": "Управление подразделениями и их иерархией (дерево через self-referential parent_id).",
        },
    ],
)

app.include_router(departments.router)


@app.get("/", tags=["health"], summary="Проверка доступности сервиса")
def root():
    return {"status": "ok"}
