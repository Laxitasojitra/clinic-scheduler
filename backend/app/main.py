from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
<<<<<<< HEAD
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.routers import auth, scheduling, users
=======

from app.routers import auth
>>>>>>> 8df9d12187793dd9f3eeda5aadd288ed11a34f98

app = FastAPI(title="Clinic Appointment Scheduling API")

app.add_middleware(
    CORSMiddleware,
<<<<<<< HEAD
    allow_origins=["*"],  # single-service deploy: frontend is served by this same app
=======
    allow_origins=["http://localhost:5173"],  # tighten to your deployed frontend URL later
>>>>>>> 8df9d12187793dd9f3eeda5aadd288ed11a34f98
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
<<<<<<< HEAD
app.include_router(scheduling.router)
app.include_router(users.router)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")
=======
>>>>>>> 8df9d12187793dd9f3eeda5aadd288ed11a34f98


@app.get("/health")
def health():
    return {"status": "ok"}
<<<<<<< HEAD


@app.get("/")
def serve_frontend():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
=======
>>>>>>> 8df9d12187793dd9f3eeda5aadd288ed11a34f98
