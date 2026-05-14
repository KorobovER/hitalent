from fastapi import FastAPI

app = FastAPI(title="HiTalent API", version="1.0.0")


@app.get("/")
def root():
    return {"status": "ok"}
