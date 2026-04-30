import random
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File,Form
from fastapi.responses import StreamingResponse
import schemas
from database import worker_collection, fs,report_collection
from utils.security import verify_password, hash_password
from utils.email_utils import send_reset_otp_email
from auth import create_access_token, get_current_worker
from bson import ObjectId
from datetime import datetime, timedelta
import math
import cloudinary
import cloudinary.uploader
from utils.cloudinary_config import cloudinary

router = APIRouter()

def generate_otp():
    return "".join([str(random.randint(0, 9)) for _ in range(6)])

@router.post("/login")
async def login(worker: schemas.WorkerLogin):
    db_worker = await worker_collection.find_one({"email": worker.email})

    if not db_worker:
        raise HTTPException(status_code=401, detail="Worker not found")

    # Debugging
    print(f"--- Login Attempt for {worker.email} ---")
    print("Keys in DB document:", list(db_worker.keys()))
    if "password" in db_worker:
        print(f"Password in DB starts with: {db_worker['password'][:5]}...")
    if "otp" in db_worker:
        print(f"OTP in DB: {db_worker['otp']}")
    
    # Check if login is with OTP or Password
    is_otp_login = False
    is_first_login = False
    
    db_otp = str(db_worker.get("otp", ""))
    
    if db_otp and db_otp == str(worker.password):
        print("-> Matched via OTP")
        is_otp_login = True
        # Mark for mandatory password change
        is_first_login = True
    elif "password" in db_worker:
        try:
            if verify_password(worker.password, db_worker["password"]):
                print("-> Matched via Bcrypt Password")
                is_first_login = db_worker.get("is_first_login", True)
            else:
                print("-> Bcrypt Password Mismatch!")
                raise HTTPException(status_code=401, detail="Invalid credentials (password mismatch)")
        except ValueError as e:
            # This happens if the password in DB is plain text and not a valid bcrypt hash
            print(f"Bcrypt ValueError parsing hash for {worker.email}: {e}")
            if worker.password == db_worker["password"]:
                # Fallback: exact plain text match (e.g. they inserted it manually without hashing)
                print("-> Matched via Plaintext Password")
                is_first_login = db_worker.get("is_first_login", True)
            else:
                print("-> Plaintext Password Mismatch!")
                raise HTTPException(status_code=401, detail="Invalid credentials (hash error)")
    else:
        print("-> Document has NO 'password' and NO matching 'otp'")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"worker_id": str(db_worker["_id"])})

    # If it was an OTP login, we should probably clear the OTP after successful token generation
    if is_otp_login:
        await worker_collection.update_one(
            {"_id": db_worker["_id"]},
            {"$unset": {"otp": ""}}
        )

    return {
        "access_token": token,
        "worker_id": str(db_worker["_id"]),
        "is_first_login": is_first_login
    }


@router.post("/register")
async def register(worker: schemas.WorkerCreate):
    existing = await worker_collection.find_one({"email": worker.email})

    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    # Generate an initial OTP for the first login
    initial_otp = generate_otp()

    new_worker = {
        "name": worker.name,
        "email": worker.email,
        "password": hash_password(worker.password),
        "phone": worker.phone,
        "status": "active",
        "tasks_completed": 0,
        "rating": 5.0,
        "otp": initial_otp,
        "is_first_login": True
    }

    result = await worker_collection.insert_one(new_worker)

    return {
        "worker_id": str(result.inserted_id),
        "initial_otp": initial_otp  # In real life, send this via SMS/Email
    }

@router.post("/change-password")
async def change_password(data: dict):
    worker_id = data.get("worker_id")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")
    
    if not all([worker_id, new_password, confirm_password]):
        raise HTTPException(status_code=400, detail="Missing fields")
    
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
        
    db_worker = await worker_collection.find_one({"_id": ObjectId(worker_id)})
    if not db_worker:
        raise HTTPException(status_code=404, detail="Worker not found")
        
    await worker_collection.update_one(
        {"_id": ObjectId(worker_id)},
        {"$set": {
            "password": hash_password(new_password),
            "is_first_login": False
        }}
    )
    return {"message": "Password updated successfully. Please login again."}

@router.post("/forgot-password")
async def forgot_password(data: dict):
    email = data.get("email")
    db_worker = await worker_collection.find_one({"email": email})
    if not db_worker:
        raise HTTPException(status_code=404, detail="Email not found")
    
    otp = generate_otp()
    # Log to terminal for developer testing
    print(f"\n--- FORGOT PASSWORD OTP ---")
    print(f"Email: {email}")
    print(f"6-digit CODE: {otp}")
    print(f"---------------------------\n")

    # Send actual email via SMTP
    email_success = await send_reset_otp_email(email, otp)
    if not email_success:
        print(f"!!! Warning: Could not send actual email to {email}")

    await worker_collection.update_one(
        {"email": email},
        {"$set": {"reset_otp": otp}}
    )
    
    # In a real app, send OTP to email. Here we just return it for testing.
    return {"message": "6-digit code sent to your email", "otp": otp}

@router.post("/verify-otp")
async def verify_otp(data: dict):
    email = data.get("email")
    otp = data.get("otp")
    
    db_worker = await worker_collection.find_one({"email": email, "reset_otp": otp})
    if not db_worker:
        raise HTTPException(status_code=400, detail="Invalid OTP or Email")
        
    return {"message": "OTP verified successfully"}

@router.post("/reset-password")
async def reset_password(data: dict):
    email = data.get("email")
    otp = data.get("otp")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")
    
    if not all([email, otp, new_password, confirm_password]):
        raise HTTPException(status_code=400, detail="Missing fields")

    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
        
    db_worker = await worker_collection.find_one({"email": email, "reset_otp": otp})
    if not db_worker:
        raise HTTPException(status_code=400, detail="Invalid OTP or session expired")
        
    await worker_collection.update_one(
        {"email": email},
        {
            "$set": {"password": hash_password(new_password)},
            "$unset": {"reset_otp": ""}
        }
    )
    
    return {"message": "Password reset successfully"}

@router.get("/profile/{worker_id}")
async def get_profile(worker_id: str):

    worker_obj_id = ObjectId(worker_id)

    worker = await worker_collection.find_one({"_id": worker_obj_id})
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
 # Completed reports
    completed_count = await report_collection.count_documents({
        "worker_id": worker_obj_id,
        "status": "completed"
    })

    pending_count = await report_collection.count_documents({
        "worker_id": worker_obj_id,
        "status": {"$in": ["assigned", "in-progress"]}
    })


    # Weekly activity
    pipeline = [
        {
            "$match": {
                "worker_id": worker_obj_id,
                "status": "completed",
                "completed_at": {"$ne": None}
            }
        },
        {
            "$group": {
            "_id": { "$dayOfWeek": "$completed_at" },  # ✅ THIS IS FIX
            "count": {"$sum": 1}
            }
        }
    ]

    weekly_raw = await report_collection.aggregate(pipeline).to_list(None)

    days_map = {
        1: "Sun", 2: "Mon", 3: "Tue",
        4: "Wed", 5: "Thu", 6: "Fri", 7: "Sat"
    }

    weekly_activity = {
        "Mon": 0, "Tue": 0, "Wed": 0,
        "Thu": 0, "Fri": 0, "Sat": 0, "Sun": 0
    }

    for item in weekly_raw:
        day = days_map[item["_id"]]
        weekly_activity[day] = item["count"]

    # Efficiency
    total_assigned = await report_collection.count_documents({
        "worker_id": worker_obj_id
    })

    efficiency = 0
    if total_assigned > 0:
        efficiency = completed_count / total_assigned


    worker["id"] = str(worker["_id"])
    del worker["_id"]

    if "password" in worker:
        del worker["password"]
        
    # Convert any other ObjectId fields to string
    for key, value in worker.items():
        if isinstance(value, ObjectId):
            worker[key] = str(value)
     # ✅ Smart insight
    if efficiency > 0.8:
        insight = "excellent"
    elif efficiency > 0.5:
        insight = "good"
    else:
        insight = "bad"

    worker["tasks_completed"] = completed_count
    worker["efficiency"] = round(efficiency, 2)
    worker["weekly_activity"] = weekly_activity
    worker["insight"] = insight
    worker["pending_tasks"] = pending_count
    return worker

@router.get("/completed-reports/{worker_id}")
async def get_completed_reports(worker_id: str):
    try:
        reports = []

        cursor = report_collection.find({
            "worker_id": ObjectId(worker_id),
            "status": "completed"
        })

        async for report in cursor:
            reports.append({
                "reportId": report.get("reportId") or str(report.get("_id")),
                "status": report.get("status"),
                "timestamp": report.get("timestamp").isoformat() if report.get("timestamp") else None,
                "address": report.get("address", "No address available"),
                "completed_at": report.get("completed_at").isoformat() if report.get("completed_at") else None,
                "image_url": report.get("image_url"),
                "after_image_url": report.get("after_image_url"),
                "model_result": report.get("model_result"),
            })

        return reports

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/profile/{worker_id}")
async def update_profile(worker_id: str, data: dict):
    # Only allow updating certain fields
    allowed_fields = ["name", "phone", "email"]
    update_data = {k: v for k, v in data.items() if k in allowed_fields}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")
        
    result = await worker_collection.update_one(
        {"_id": ObjectId(worker_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Worker not found")
        
    return {"message": "Profile updated successfully"}

@router.post("/{worker_id}/profile-image")
async def upload_profile_image(worker_id: str, file: UploadFile = File(...)):
    """
    Uploads a profile image to GridFS and updates the worker document.
    """
    try:
        from bson import ObjectId
        # Verify worker exists
        worker = await worker_collection.find_one({"_id": ObjectId(worker_id)})
        if not worker:
            raise HTTPException(status_code=404, detail="Worker not found")

        # Upload to cloudinary
        upload_result = cloudinary.uploader.upload(
            file.file,
            folder="worker_profiles"
        )

        image_url = upload_result.get("secure_url")

        # Update worker document with the new file_id
        await worker_collection.update_one(
            {"_id": ObjectId(worker_id)},
            {"$set": {"profile_image_id": str(image_url)}}
        )

        return {"message": "Image uploaded successfully", "image_url": image_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profile-image/{worker_id}")
async def get_profile_image(worker_id: str):
    """
    Streams the worker's profile image from GridFS.
    """
    try:
        from bson import ObjectId
        worker = await worker_collection.find_one({"_id": ObjectId(worker_id)})
        if not worker or "profile_image_id" not in worker:
            raise HTTPException(status_code=404, detail="Profile image not found")

        return {
            "image_url": worker["profile_image_id"]
        }
        
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/assigned-reports/{worker_id}")
async def get_assigned_reports(worker_id: str):
    try:
        reports = []

        cursor = report_collection.find({
            "worker_id": ObjectId(worker_id),  
            "status": {"$in": ["assigned", "in-progress"]}
        })

        async for report in cursor:
            # Build a JSON-serializable report dict preserving original fields
            reports.append({
                "reportId": report.get("reportId") or str(report.get("_id")),
                "user_id": report.get("user_id", ""),
                "username": report.get("username", ""),
                "image_url": report.get("image_url", ""),
                "address": report.get("address", "No address available"),
                "location": {
                    "lat": report.get("location", {}).get("lat", 0.0),
                    "lng": report.get("location", {}).get("lng", 0.0),
                },
                "status": report.get("status", "pending"),
                # prefer ISO string for timestamp so client parsing is reliable
                "timestamp": report.get("timestamp").isoformat() if isinstance(report.get("timestamp"), datetime) else report.get("timestamp"),
                "model_result": report.get("model_result"),
                "after_image_url": report.get("after_image_url"),
                "completed_at": report.get("completed_at").isoformat() if isinstance(report.get("completed_at"), datetime) else report.get("completed_at"),
                "is_genuine": report.get("is_genuine", True),
                "updatedAt": report.get("updatedAt").isoformat() if isinstance(report.get("updatedAt"), datetime) else report.get("updatedAt"),
                # ensure worker_id is a string
                "worker_id": str(report.get("worker_id")) if report.get("worker_id") is not None else None,
            })

        return reports

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km

    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)

    a = (math.sin(dLat/2) ** 2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dLon/2) ** 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c  # distance in KM


@router.post("/complete-report")
async def complete_report(
    report_id: str = Form(...),
    worker_lat: float = Form(...),
    worker_lng: float = Form(...),
    file: UploadFile = File(...)
):
    try:
        report = await report_collection.find_one({"reportId": report_id})

        # if not report:
        #     raise HTTPException(status_code=404, detail="Report not found")
            

        report_lat = report["location"]["lat"]
        report_lng = report["location"]["lng"]

        distance = calculate_distance(worker_lat, worker_lng, report_lat, report_lng)

        # 🔥 Location validation
        if distance > 0.1:
            raise HTTPException(status_code=400, detail="Too far from location")

        # Upload to cloudinary
        upload_result = cloudinary.uploader.upload(
            file.file,
            folder="garbage_reports_after"
        )

        image_url = upload_result.get("secure_url")

        # Update DB
        await report_collection.update_one(
            {"reportId": report_id},
            {
                "$set": {
                    "status": "completed",
                    "after_image_url": image_url,
                    "completed_at": datetime.utcnow(),
                    "worker_location": {
                        "lat": worker_lat,
                        "lng": worker_lng
                    }
                }
            }
        )

        return {"message": "Report completed successfully",
                "image_url": image_url}
    except HTTPException as e:
    # ✅ DO NOT convert this
        raise e

    except Exception as e:
        print("ERROR in complete_report:", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update-location")
async def update_location(data: dict):
    try:
        worker_id = data.get("worker_id")
        lat = data.get("lat")
        lng = data.get("lng")

        if not all([worker_id, lat, lng]):
            raise HTTPException(status_code=400, detail="Missing fields")

        await worker_collection.update_one(
            {"_id": ObjectId(worker_id)},
            {
                "$set": {
                    "location": {
                        "lat": lat,
                        "lng": lng
                    },
                    "last_updated": datetime.utcnow()
                }
            }
        )

        return {"message": "Location updated"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
