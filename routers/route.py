from fastapi import APIRouter
from typing import List
import math
# from database import report_collection

router = APIRouter()

def calculate_distance(lat1, lon1, lat2, lon2):
    # Haversine distance would be better, but for local routes Euclidean is often enough
    # Let's use Euclidean for simplicity as requested "update", but make it better
    return math.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)

# @router.get("/fix-db")
# async def fix_db():

#     await report_collection.update_many(
#         {},
#         {
#             "$set": {
#                 "assigned_worker_id": None,
#                 "assigned_at": None,
#                 "completed_at": None,
#                 "after_image_url": None
#             }
#         }
#     )
#     return {"message": "DB Updated"}

@router.post("/optimize-route")
# async def optimize_route(data: dict):
#     """
#     Optimizes route using Nearest Neighbor with Severity weighting.
#     """
#     current = data["currentLocation"]
#     tasks = data["tasks"]
    
#     if not tasks:
#         return {"order": []}

#     optimized_order = []
#     unvisited = list(tasks)
#     curr_lat = current["latitude"]
#     curr_lon = current["longitude"]

#     while unvisited:
#         best_task = None
#         best_score = float('inf')
        
#         for task in unvisited:
#             # Handle the nested location format from 'reports' collection
#             task_lat = task.get("location", {}).get("lat", 12.9716)
#             task_lon = task.get("location", {}).get("lng", 77.5946)
            
#             dist = calculate_distance(curr_lat, curr_lon, task_lat, task_lon)
            
#             # Severity factor
#             severity_weight = 0.5 if task.get("severity") == "HIGH" else 1.0
#             # Higher fill level reduces effective distance
#             fill_level = float(task.get("fillLevel", 0))
#             fill_level_weight = 1.0 - (fill_level / 2.0) if fill_level < 1.0 else 0.1
            
#             score = dist * severity_weight * fill_level_weight
            
#             if score < best_score:
#                 best_score = score
#                 best_task = task
        
#         optimized_order.append(best_task["id"])
#         unvisited.remove(best_task)
#         curr_lat = best_task.get("location", {}).get("lat", 12.9716)
#         curr_lon = best_task.get("location", {}).get("lng", 77.5946)

#     return {"order": optimized_order}

async def optimize_route(data: dict):
    try:
        # ✅ FIX: match Flutter format
        current = data.get("currentLocation", {})
        tasks = data.get("tasks", [])

        if not tasks:
            return {"order": []}

        optimized_order = []
        unvisited = list(tasks)

        curr_lat = current.get("latitude")
        curr_lon = current.get("longitude")

        if curr_lat is None or curr_lon is None:
            return {"error": "Invalid current location"}

        while unvisited:
            best_task = None
            best_score = float('inf')

            for task in unvisited:
                loc = task.get("location", {})

                task_lat = loc.get("lat")
                task_lon = loc.get("lng")

                if task_lat is None or task_lon is None:
                    continue

                dist = calculate_distance(curr_lat, curr_lon, task_lat, task_lon)

                # 🔥 Smart Priority weighting
                # LOWer weight means HIGHer priority (shorter effective distance)
                severity = task.get("model_result", {}) \
               .get("sustainability_summary", {}) \
               .get("severity", "Low")

                severity_weight = 0.4 if severity == "High" else (0.7 if severity == "Medium" else 1.0)
                fill_level = float(task.get("fillLevel", 0))
                
                # Fill level 0.0 to 1.0. A fill of 1.0 (100%) should have extreme priority.
                # Priority factor: 1.0 for empty, moves towards 0.2 for full.
                fill_weight = 1.0 - (fill_level * 0.8) 

                # Combine distance and priority
                # Effective score = real_distance * priority_modifiers
                score = dist * severity_weight * fill_weight

                if score < best_score:
                    best_score = score
                    best_task = task

            if best_task is None:
                break

            optimized_order.append(best_task["id"])
            unvisited.remove(best_task)

            curr_lat = best_task["location"]["lat"]
            curr_lon = best_task["location"]["lng"]

        return {"order": optimized_order}

    except Exception as e:
        return {"error": str(e)}