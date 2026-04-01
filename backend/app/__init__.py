from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .utils.import_algorithms import load_algorithms

app = FastAPI(title="Chess AI Backend")

# Allow CORS for local frontend during development and production
app.add_middleware(
	CORSMiddleware,
	allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000", "https://app.jeetumodi.me", "https://chess.jeetumodi.me"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Load algorithm modules once at startup
alg_modules = load_algorithms()

# Register routers (imported late to avoid circulars)
from .routers import health, algorithms as algorithms_router
from .routers import arena as arena_router

app.include_router(health.router)
app.include_router(algorithms_router.get_router(alg_modules))
app.include_router(arena_router.get_arena_router(alg_modules))

__all__ = ["app", "alg_modules"]
