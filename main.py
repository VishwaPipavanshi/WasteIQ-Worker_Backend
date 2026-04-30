from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import worker, route
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="WasteIQ - Smart Garbage Worker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(worker.router, prefix="/worker", tags=["Worker"])
# app.include_router(task.router, prefix="/task", tags=["Task"])
app.include_router(route.router, tags=["Route"])

# Create uploads directory if it doesn't exist
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
def home():
    return {"message": "MongoDB Backend Running 🚀"}