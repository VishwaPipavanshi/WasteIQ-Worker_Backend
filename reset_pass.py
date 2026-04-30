import asyncio
import bcrypt
from motor.motor_asyncio import AsyncIOMotorClient

async def run():
    client = AsyncIOMotorClient('mongodb+srv://vpipavanshi_db_user:Vishwa2004@cluster0.kntn9pq.mongodb.net/?appName=Cluster0')
    collection = client['test']['workers']
    new_hash = bcrypt.hashpw(b'123456', bcrypt.gensalt()).decode('utf-8')
    await collection.update_one(
        {'email': 'romilpolara49@gmail.com'},
        {'$set': {'password': new_hash, 'is_first_login': True}}
    )
    print('Password reset to 123456')

asyncio.run(run())
