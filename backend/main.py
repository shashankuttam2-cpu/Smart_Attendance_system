import os
import shutil
import asyncio
from datetime import date, datetime
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import db
from face_engine import face_engine
from scheduler import scheduler

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for ESP32 BLE Beacon Digital Geofence & AI Facial Recognition Attendance System",
    version="1.0.0"
)

# Enable CORS for Flutter mobile app, local emulators, and web interfaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------
# Startup Event: Launch Background Timetable Scheduler
# ------------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    print("[Main] Initializing Smart Attendance System...")
    # Trigger background timetable cron worker
    asyncio.create_task(scheduler.run_cron_loop())
    # Pre-check face engine readiness
    if face_engine.is_ready():
        print("[Main] AI Face Recognition Engine is READY.")
    else:
        print("[Main] Warning: AI Face models are still initializing.")

# ------------------------------------------------------------------------------
# System Health & Status
# ------------------------------------------------------------------------------
@app.get("/api/v1/system/status")
def get_system_status():
    today_records = db.get_attendance_logs(query_date=date.today().isoformat())
    students = db.get_all_students()
    return {
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "models_ready": face_engine.is_ready(),
        "active_geofence": {
            "room_id": settings.DEFAULT_ROOM_ID,
            "room_name": settings.DEFAULT_ROOM_NAME,
            "beacon_uuid": settings.BEACON_UUID,
            "min_rssi_threshold": settings.MIN_RSSI_THRESHOLD
        },
        "statistics": {
            "total_students_enrolled": len(students),
            "today_attendance_count": len(today_records),
            "active_class": db.get_active_class()
        }
    }

# ------------------------------------------------------------------------------
# API 1: /register (Admin Student Enrollment)
# ------------------------------------------------------------------------------
@app.post("/api/v1/register")
async def register_student(
    name: str = Form(..., description="Full Name of Student"),
    roll_no: str = Form(..., description="Unique College Roll Number"),
    department: str = Form("Computer Science", description="Branch/Department"),
    photo: UploadFile = File(..., description="Clear front-facing photo of the student")
):
    """
    Enrolls a student:
    1. Reads uploaded photo bytes.
    2. Runs AI Face Engine to detect face and compute 128-d mathematical embedding.
    3. Saves photo to disk and stores profile + vector in database.
    """
    if not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a valid image (JPEG/PNG).")

    photo_bytes = await photo.read()
    if len(photo_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty image uploaded.")

    # Extract 128-d face features
    try:
        encoding = face_engine.extract_encoding_from_bytes(photo_bytes)
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=503, detail=str(re))

    # Save photo to local disk
    clean_roll = roll_no.strip().upper().replace("/", "_")
    photo_filename = f"{clean_roll}.jpg"
    photo_filepath = os.path.join(settings.PHOTOS_DIR, photo_filename)
    with open(photo_filepath, "wb") as f:
        f.write(photo_bytes)

    # Persist in SQLite database
    student_id = db.add_student(
        name=name.strip(),
        roll_no=roll_no.strip().upper(),
        face_encoding=encoding,
        photo_path=photo_filepath,
        department=department.strip()
    )

    return {
        "success": True,
        "message": f"Student '{name}' registered successfully with Roll No '{roll_no}'.",
        "student": {
            "id": student_id,
            "name": name.strip(),
            "roll_no": roll_no.strip().upper(),
            "department": department.strip(),
            "encoding_length": len(encoding)
        }
    }

# ------------------------------------------------------------------------------
# API 2: /verify (Mobile App Live Attendance Verification)
# ------------------------------------------------------------------------------
@app.post("/api/v1/verify")
async def verify_attendance(
    photo: UploadFile = File(..., description="Live camera selfie captured inside classroom"),
    room_id: str = Form(settings.DEFAULT_ROOM_ID, description="Detected Classroom Identifier"),
    beacon_uuid: Optional[str] = Form(None, description="BLE Beacon UUID discovered by phone"),
    rssi: Optional[int] = Form(None, description="Signal strength in dBm from ESP32")
):
    """
    Verifies student physical presence and marks attendance:
    1. Geofence Check: Validates room_id, beacon_uuid, and RSSI threshold (>= -75 dBm).
    2. AI Face Recognition: Compares selfie against enrolled student embeddings.
    3. Records punch-in timestamp in database if tolerance < 0.6.
    """
    # 1. Geofence Validation
    if beacon_uuid and beacon_uuid.lower() != settings.BEACON_UUID.lower():
        raise HTTPException(
            status_code=403, 
            detail=f"Geofence Mismatch: Scanned Beacon UUID ({beacon_uuid}) does not match classroom beacon."
        )

    if rssi is not None and rssi < settings.MIN_RSSI_THRESHOLD:
        raise HTTPException(
            status_code=403, 
            detail=f"Signal Too Weak ({rssi} dBm). Please enter the classroom to mark attendance."
        )

    # 2. Extract live selfie encoding
    photo_bytes = await photo.read()
    try:
        live_encoding = face_engine.extract_encoding_from_bytes(photo_bytes)
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=f"Face recognition error: {str(ve)}")
    except RuntimeError as re:
        raise HTTPException(status_code=503, detail=str(re))

    # 3. Retrieve all candidate student vectors
    candidates = db.get_all_student_encodings()
    if not candidates:
        raise HTTPException(
            status_code=404, 
            detail="No enrolled students found in database. Please register students first."
        )

    # 4. Perform vector matching
    matched_student, distance = face_engine.find_best_match(
        live_encoding=live_encoding,
        candidates=candidates,
        tolerance=settings.FACE_MATCH_TOLERANCE
    )

    if not matched_student:
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "match": False,
                "message": "Face mismatch: Your face does not match any registered student in this class.",
                "distance": distance,
                "tolerance": settings.FACE_MATCH_TOLERANCE
            }
        )

    # 5. Record attendance in database
    result = db.record_attendance(
        roll_no=matched_student["roll_no"],
        student_name=matched_student["name"],
        room_id=room_id,
        confidence=distance,
        rssi=rssi
    )

    return {
        "success": True,
        "match": True,
        "message": f"Attendance verified successfully for {matched_student['name']}!",
        "roll_no": matched_student["roll_no"],
        "student_name": matched_student["name"],
        "room_id": room_id,
        "recorded_time": result["recorded_time"],
        "already_marked": result["already_marked"],
        "status": result["status"],
        "match_confidence": distance,
        "rssi": rssi
    }

# ------------------------------------------------------------------------------
# Attendance & Student Management Endpoints
# ------------------------------------------------------------------------------
@app.get("/api/v1/students")
def list_students():
    return db.get_all_students()

@app.get("/api/v1/attendance")
def list_attendance(
    target_date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    room_id: Optional[str] = Query(None, description="Filter by Room ID")
):
    query_date = target_date or date.today().isoformat()
    records = db.get_attendance_logs(query_date=query_date, room_id=room_id)
    return {
        "date": query_date,
        "room_id": room_id or "ALL",
        "total_records": len(records),
        "records": records
    }

@app.get("/api/v1/classes")
def list_classes():
    return db.get_all_classes()

# ------------------------------------------------------------------------------
# Report Generation & Email Dispatch
# ------------------------------------------------------------------------------
@app.post("/api/v1/report/generate")
def trigger_report(
    class_id: Optional[int] = Form(None, description="Optional Class ID to compile report for"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Triggers on-demand Excel generation and email transmission for a class session."""
    classes = db.get_all_classes()
    target_class = None
    if class_id:
        target_class = next((c for c in classes if c["id"] == class_id), None)
    if not target_class and classes:
        target_class = classes[0]

    if not target_class:
        raise HTTPException(status_code=404, detail="No class schedules configured.")

    report_path = scheduler.process_class_end(target_class)
    return {
        "success": True,
        "message": f"Report generated and dispatched for {target_class['subject_code']}.",
        "file_name": os.path.basename(report_path),
        "download_url": f"/api/v1/report/download/{os.path.basename(report_path)}"
    }

@app.get("/api/v1/report/download/{filename}")
def download_report(filename: str):
    file_path = os.path.join(settings.REPORTS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report file not found.")
    return FileResponse(
        file_path, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename
    )

# ------------------------------------------------------------------------------
# Mount Glassmorphic Admin Dashboard & Web Simulation
# ------------------------------------------------------------------------------
static_dir = os.path.join(settings.BASE_DIR, "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
