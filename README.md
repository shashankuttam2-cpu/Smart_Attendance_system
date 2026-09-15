# IERT Smart Attendance System
### ESP32 BLE Beacon Digital Geofence + AI Facial Recognition Engine + Cross-Platform Mobile App

An enterprise-grade, privacy-focused IoT and Computer Vision attendance automation system designed for higher-education classrooms and laboratory sessions.

---

## 🏛️ System Architecture

```
                                  ┌───────────────────────────────┐
                                  │      ESP32 BLE Beacon         │
                                  │   (Classroom Digital Fence)   │
                                  │      UUID + Major/Minor       │
                                  └──────────────┬────────────────┘
                                                 │
                                                 │ 5-10m BLE Broadcast
                                                 ▼
┌───────────────────────────────┐        ┌───────────────────────────────┐
│     Faculty Email Inbox       │        │     Student Smartphone        │
│   (Automated .xlsx Report)    │        │   (Flutter Mobile / Web)      │
└──────────────▲────────────────┘        └──────────────┬────────────────┘
               │                                        │
               │ Auto-cron at class end                 │ 1. Check RSSI >= -75 dBm
               │                                        │ 2. Live Front Camera Selfie
               │                                        │    (POST /api/v1/verify)
               │                                        ▼
      ┌────────┴────────────────────────────────────────────────┐
      │             Python FastAPI AI Backend                   │
      │   - OpenCV DNN SFace + YuNet (128-d Deep Embeddings)   │
      │   - SQLite Persistent Biometric Storage                 │
      │   - Automated Excel (.xlsx) Report Generator            │
      └─────────────────────────────────────────────────────────┘
```

---

## 📦 Directory Structure

```text
smart_attendance_system/
├── hardware_esp32/
│   ├── IERT_BLE_Beacon.ino           # Arduino C++ sketch for ESP32 BLE beacon
│   └── README_HARDWARE.md            # Hardware wiring, flashing, and Tx calibration
├── backend/
│   ├── main.py                       # FastAPI server (API 1: /register, API 2: /verify)
│   ├── config.py                     # Central configuration (UUID, RSSI, thresholds, SMTP)
│   ├── database.py                   # SQLite database (Students, Attendance, Timetable)
│   ├── face_engine.py                # Dual AI engine (OpenCV SFace/YuNet + dlib fallback)
│   ├── scheduler.py                  # Timetable cron runner & automated email dispatcher
│   ├── requirements.txt              # Backend dependencies
│   ├── models/                       # Deep learning ONNX model weights
│   │   ├── face_detection_yunet_2023mar.onnx
│   │   └── face_recognition_sface_2021dec.onnx
│   ├── static/                       # Premium Glassmorphic Web Dashboard & Simulator
│   │   ├── index.html
│   │   ├── style.css
│   │   └── app.js
│   └── data/                         # SQLite DB, enrolled student photos, and reports
├── mobile_app_flutter/
│   ├── pubspec.yaml                  # Flutter package dependencies
│   ├── lib/
│   │   ├── main.dart                 # App entrypoint and camera initialization
│   │   ├── screens/
│   │   │   ├── home_screen.dart      # Mark Attendance UI with BLE scanner
│   │   │   └── attendance_result_screen.dart # Feedback card (Success / Mismatch / Out of bounds)
│   │   └── services/
│   │       ├── ble_service.dart      # flutter_blue_plus geofence & RSSI check
│   │       └── api_service.dart      # Multipart upload to backend /verify
│   └── README_MOBILE.md              # Android/iOS setup & build guide
└── README.md                         # Project documentation
```

---

## ⚡ Quick Start Guide

### Step 1: Start the Backend AI Server & Dashboard
1. Open PowerShell or Terminal and navigate to `backend/`:
   ```bash
   cd smart_attendance_system/backend
   ```
2. Start the FastAPI server using Python:
   ```bash
   python main.py
   ```
3. Open your web browser at:
   **`http://localhost:8000`**

### Step 2: Test End-to-End Immediately via Web Simulator
1. Open the **"Enroll Student"** tab:
   - Enter Name (e.g. `Shashank Uttam`), Roll No (`21CS042`), and snap or upload a photo.
   - The AI extracts the 128-d facial vector and enrolls the student.
2. Open the **"Student Mobile Simulator"** tab:
   - Make sure **"Inside Classroom (-62 dBm)"** is selected.
   - Click **"Mark Attendance"**.
   - Watch the AI match your face in $< 100\text{ ms}$, sound a chime, and record your attendance!
   - Now switch the radio to **"Outside Corridor (-84 dBm)"** and click **"Mark Attendance"** $\rightarrow$ Observe the geofence rejection: *"Signal too weak (-84 dBm). Please enter the classroom."*
3. Open the **"Excel Reports & Timetable"** tab:
   - Click **"Compile & Download Excel Report"** to inspect the auto-generated multi-sheet `.xlsx` spreadsheet.

### Step 3: Deploy Module 1 (Hardware ESP32 Beacon)
1. Connect your ESP32 board to your PC via USB.
2. Open `hardware_esp32/IERT_BLE_Beacon.ino` in Arduino IDE.
3. Select board `ESP32 Dev Module`, choose your COM port, and click **Upload**.
4. Unplug from PC and plug into any 5V mobile charger in Room 302.

### Step 4: Deploy Module 3 (Flutter Mobile App)
1. Open `mobile_app_flutter/lib/services/api_service.dart` and set `baseUrl` to your computer's local Wi-Fi IP.
2. Run `flutter pub get` and `flutter run`.

---

## 🔍 REST API Specifications

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/register` | Multipart upload (`name`, `roll_no`, `department`, `photo`). Extracts 128-d features and saves to DB. |
| `POST` | `/api/v1/verify` | Multipart upload (`photo`, `room_id`, `beacon_uuid`, `rssi`). Validates geofence, matches face ($\text{tolerance} < 0.6$), marks attendance. |
| `GET`  | `/api/v1/system/status` | Current active room, beacon UUID, enrolled student count, and today's attendance total. |
| `GET`  | `/api/v1/students` | Lists all enrolled student records. |
| `GET`  | `/api/v1/attendance` | Returns attendance logs for today or filtered by date and room. |
| `POST` | `/api/v1/report/generate` | Generates a formatted session Excel file and dispatches an email to the faculty member. |
| `GET`  | `/api/v1/report/download/{file}` | Downloads the generated `.xlsx` report directly from the server. |
