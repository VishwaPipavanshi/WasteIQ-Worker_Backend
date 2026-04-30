from sqlalchemy.orm import Session
import models
from utils.security import hash_password

def create_worker(db: Session, worker):

    db_worker = models.Worker(
        name=worker.name,
        email=worker.email,
        password=hash_password(worker.password),
        phone=worker.phone
    )

    db.add(db_worker)
    db.commit()
    db.refresh(db_worker)

    return db_worker


def get_worker_by_email(db: Session, email: str):
    return db.query(models.Worker).filter(models.Worker.email == email).first()


def get_worker_tasks(db: Session, worker_id: int):
    return db.query(models.Task).filter(models.Task.worker_id == worker_id).all()