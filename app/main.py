from fastapi import FastAPI
from dotenv import load_dotenv

from app.api import agent, application, auth, github, job, profile
from app.api.fill_packet import router as fill_packet_router
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(title="Job Filler Agent API", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok"}

# Routers
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(profile.resume_router)
app.include_router(github.router)
app.include_router(job.router)
app.include_router(agent.router)
app.include_router(application.router)

# Your packet endpoint
app.include_router(fill_packet_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # fine for local dev; tighten later for EC2
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
