from fastapi import FastAPI
from src.api.routers import router
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.adapters.sqlite import ensure_db, init_schema

from src.config import get_api_config
import shutil

cfg = get_api_config()

app = FastAPI(title="RowIO API", version="v1-3", debug=True, redirect_slashes=False)

# DEV: allow everything so preflight gets a 200
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],      # must include OPTIONS
    allow_headers=["*"],
    allow_credentials=False,  # keep False if using "*"
    max_age=86400,
)

app.mount("/videos", StaticFiles(directory=str(cfg.STORAGE_DIR / "videos")), name="videos")
app.include_router(router, prefix="/rowio")

@app.on_event("startup")
def on_startup():
    wipe_on_start = True

    if wipe_on_start:
        # wipe videos file
        filepath = cfg.STORAGE_DIR / "videos"
        if filepath.exists():
            shutil.rmtree(filepath)


    conn = ensure_db()
    try:
        if wipe_on_start:
            init_schema(conn)
        pass
    finally:
        conn.close()
