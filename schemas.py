from pydantic import BaseModel, Field
from typing import Optional, List

class WorkerLogin(BaseModel):
    email: str
    password: str

class WorkerCreate(BaseModel):
    name: str
    email: str
    password: str
    phone: str

class WorkerProfile(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    status: str
    tasks_completed: int
    rating: float

class Task(BaseModel):
    id: Optional[str]
    title: str
    description: str
    status: str = "pending"
    worker_id: str
    latitude: float
    longitude: float
    severity: str = "LOW"
    binFillLevel: int = 0

class RouteOptimizationRequest(BaseModel):
    currentLocation: dict
    tasks: List[dict]