# from passlib.context import CryptContext

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# def hash_password(password: str):
#     return pwd_context.hash(password)


# def verify_password(plain, hashed):
#     return pwd_context.verify(plain, hashed)
import bcrypt

def hash_password(password: str):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str):
    return bcrypt.checkpw(
        password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )