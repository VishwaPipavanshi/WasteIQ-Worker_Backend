from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from database import worker_collection
from bson import ObjectId

SECRET_KEY = "SECRET123"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="worker/login")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=10)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_worker(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        worker_id: str = payload.get("worker_id")
        if worker_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    worker = await worker_collection.find_one({"_id": ObjectId(worker_id)})
    if worker is None:
        raise credentials_exception
    
    worker["id"] = str(worker["_id"])
    return worker