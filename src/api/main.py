# src/api/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("PhilCongressAI API starting")
    yield
    print("PhilCongressAI API stopping")


app = FastAPI(
    title="PhilCongressAI API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
