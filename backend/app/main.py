from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth

app = FastAPI(title="Clinic Appointment Scheduling API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # tighten to your deployed frontend URL later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.get("/health")
def health():
    return {"status": "ok"}
