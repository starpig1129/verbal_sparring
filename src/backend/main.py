from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.api.routes.auth import router as auth_router

app = FastAPI(title="唇槍舌戰 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        A JSON object with ``{"status": "ok"}`` when the service is running.
    """
    return {"status": "ok"}
