from fastapi import FastAPI

from .utils.import_algorithms import load_algorithms

app = FastAPI(title="Chess AI Backend")

# Load algorithm modules once at startup
alg_modules = load_algorithms()

# Register routers (imported late to avoid circulars)
from .routers import health, algorithms as algorithms_router

app.include_router(health.router)
app.include_router(algorithms_router.get_router(alg_modules))

__all__ = ["app", "alg_modules"]
