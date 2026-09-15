import os

class Settings:
    # --------------------------------------------------------------------------
    # Server & Environment
    # --------------------------------------------------------------------------
    PROJECT_NAME: str = "IERT Smart Attendance System"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # --------------------------------------------------------------------------
    # Classroom & BLE Geofence Settings (Module 1)
    # --------------------------------------------------------------------------
    DEFAULT_ROOM_ID: str = "IERT_Room_302"
    DEFAULT_ROOM_NAME: str = "Room 302 (Computer Science & Engineering)"
    BEACON_UUID: str = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
    BEACON_MAJOR: int = 1
    BEACON_MINOR: int = 302
    # RSSI Threshold: Signals weaker than -75 dBm (e.g., -80 dBm) mean the student is outside
    MIN_RSSI_THRESHOLD: int = -75

    # --------------------------------------------------------------------------
    # AI Face Recognition Parameters (Module 2)
    # --------------------------------------------------------------------------
    # Tolerance threshold (< 0.6 is a verified match; lower is stricter)
    FACE_MATCH_TOLERANCE: float = 0.60
    # Directory paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    MODELS_DIR = os.path.join(BASE_DIR, "models")
    PHOTOS_DIR = os.path.join(DATA_DIR, "student_photos")
    REPORTS_DIR = os.path.join(DATA_DIR, "reports")
    
    # Model Weights Paths
    YUNET_MODEL_PATH = os.path.join(MODELS_DIR, "face_detection_yunet_2023mar.onnx")
    SFACE_MODEL_PATH = os.path.join(MODELS_DIR, "face_recognition_sface_2021dec.onnx")

    # --------------------------------------------------------------------------
    # Database Configuration (SQLite)
    # --------------------------------------------------------------------------
    DB_PATH = os.path.join(DATA_DIR, "attendance.db")
    DATABASE_URL: str = f"sqlite:///{DB_PATH}"

    # --------------------------------------------------------------------------
    # Automated Email & SMTP Settings (Cron / Auto-Report)
    # --------------------------------------------------------------------------
    # Set to False and supply actual credentials for live production emailing
    MOCK_EMAIL_DISPATCH: bool = True 
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "attendance.iert@gmail.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    DEFAULT_TEACHER_EMAIL: str = os.getenv("DEFAULT_TEACHER_EMAIL", "teacher.cs@iert.ac.in")

settings = Settings()

# Ensure required runtime folders exist
os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.MODELS_DIR, exist_ok=True)
os.makedirs(settings.PHOTOS_DIR, exist_ok=True)
os.makedirs(settings.REPORTS_DIR, exist_ok=True)
