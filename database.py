from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket

MONGO_URL = "mongodb+srv://vpipavanshi_db_user:Vishwa2004@cluster0.kntn9pq.mongodb.net/?appName=Cluster0"

client = AsyncIOMotorClient(MONGO_URL)

db = client["test"]   # Database name

worker_collection = db["workers"]
task_collection = db["tasks"]
report_collection = db["reports"]
fs = AsyncIOMotorGridFSBucket(db)