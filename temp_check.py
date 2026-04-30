import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def run():
    try:
        client = AsyncIOMotorClient('mongodb+srv://vpipavanshi_db_user:Vishwa2004@cluster0.kntn9pq.mongodb.net/?appName=Cluster0')
        db = client['test']
        collection = db['workers']
        workers = await collection.find().to_list(100)
        for w in workers:
            print(f"Email: {w.get('email')}, OTP: {w.get('otp')}, Mobile: {w.get('mobile')}, Aadhaar: {w.get('aadhaar')}, PasswordInDB: {w.get('password')[:10] if w.get('password') else 'None'}")
    except Exception as e:
        print("Error:", e)

asyncio.run(run())
