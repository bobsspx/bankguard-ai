from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.health import router as health_router
from app.api.access import router as access_router
from app.api.auth import router as auth_router

app = FastAPI(
    title="BankGuard AI API",
    description=(
        "Banking fraud detection and "
        "security monitoring platform."
    ),
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(access_router)

@app.get("/")
def root():
    return {
        "name": "BankGuard AI",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "bankguard-api",
    }