from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.backend.api.routes.auth import router as auth_router
from src.backend.api.routes.leaderboard import router as leaderboard_router
from src.backend.api.routes.matches import router as matches_router
from src.backend.api.routes.replay import router as replay_router
from src.backend.api.ws.battle_ws import router as ws_router

app = FastAPI(title="唇槍舌戰 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(matches_router)
app.include_router(ws_router)
app.include_router(leaderboard_router)
app.include_router(replay_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# Serve built React frontend — falls back to index.html for SPA routing
_DIST = Path(__file__).parent.parent.parent / "src" / "frontend" / "dist"
if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        return FileResponse(_DIST / "index.html")
