from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, urls, analytics
import app.models  # noqa: F401
from fastapi.security import HTTPBearer

security = HTTPBearer()

app = FastAPI(
    title="URL Shortener",
    description="URL Shortener with Analytics API",
    version="1.0.0",
    swagger_ui_parameters={"persistAuthorization": True}
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check MUST be before urls router — /{short_code} catches everything
@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.BASE_URL}

# Routers — urls router last because it has catch-all /{short_code}
app.include_router(auth.router)
app.include_router(analytics.router)
app.include_router(urls.router)    # ← always last