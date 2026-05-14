from fastapi import FastAPI

from app.routers import departments

app = FastAPI(title="HiTalent API", version="1.0.0")

app.include_router(departments.router)


@app.get("/")
def root():
    return {"status": "ok"}
