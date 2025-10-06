# /src/api/app.py

from fastapi import FastAPI
from src.api.routers import router
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.adapters.sqlite import ensure_db, init_schema

from src.config import get_api_config
import shutil

cfg = get_api_config()

app = FastAPI(title="RowIO API", version="v1.4", debug=True, redirect_slashes=False)

# DEV: allow everything so preflight gets a 200
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
    max_age=86400,
)
app.mount(f"/{cfg.APP_DATA_PREFIX}", StaticFiles(directory=cfg.APP_DATA_DIR), name=cfg.APP_DATA_PREFIX)
app.include_router(router, prefix="/rowio")

@app.on_event("startup")
def on_startup():
    wipe_on_start = True

    if wipe_on_start:
        # Wipe all files, including DB
        filepath = cfg.STORAGE_DIR
        if filepath.exists():
            shutil.rmtree(filepath)


    # Ensure storage directory
    cfg.APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    cfg.EVALUATIONS_DIR.mkdir(parents=True, exist_ok=True)
    cfg.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    cfg.VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

    conn = ensure_db()
    try:
        wipe_on_start = True
        if wipe_on_start:
            init_schema(conn)
        pass
    finally:
        conn.close()
