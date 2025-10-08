from fastapi import FastAPI
from app.routers.webhooks import router as webhooks_router

app = FastAPI(title="Monday → PostgreSQL Sync", version="1.0.0")
app.include_router(webhooks_router)

@app.get("/health")
def health():
    return {"status": "ok"}
