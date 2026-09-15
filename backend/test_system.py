"""
End-to-End Automated Verification Script for IERT Smart Attendance System
"""
import os
import sys
import numpy as np
import cv2

# Set backend path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from database import db
from face_engine import face_engine
from scheduler import scheduler

def run_tests():
    print("==================================================")
    print("  IERT Smart Attendance - End-to-End System Tests")
    print("==================================================")

    # 1. Test Face Engine Readiness
    print("\n[Test 1] Verifying AI Face Recognition Engine...")
    assert face_engine.is_ready(), "Face engine failed to initialize!"
    print(" -> PASS: OpenCV YuNet Face Detector & SFace Recognizer loaded successfully.")

    # 2. Test Vector Distance Calculation & Tolerance
    print("\n[Test 2] Testing Face Vector Similarity & Tolerance Matching...")
    # Generate two random normalized 128-d vectors
    v1 = np.random.randn(128).astype(np.float32)
    v1 /= np.linalg.norm(v1)

    # Same vector must have distance ~0.0
    dist_same = face_engine.calculate_distance(v1.tolist(), v1.tolist())
    print(f" -> Distance between identical faces: {dist_same:.4f} (Expected: ~0.0000)")
    assert dist_same < 0.01, f"Identical face distance too high: {dist_same}"

    # Generate slight perturbation (same person, slight angle shift)
    v1_shifted = v1 + np.random.normal(0, 0.08, 128).astype(np.float32)
    v1_shifted /= np.linalg.norm(v1_shifted)
    dist_shifted = face_engine.calculate_distance(v1.tolist(), v1_shifted.tolist())
    print(f" -> Distance with minor natural variation: {dist_shifted:.4f} (Tolerance: < 0.60)")
    assert dist_shifted < settings.FACE_MATCH_TOLERANCE, "Shifted face rejected unexpectedly!"

    # Uncorrelated random vector (different person)
    v2 = np.random.randn(128).astype(np.float32)
    v2 /= np.linalg.norm(v2)
    dist_diff = face_engine.calculate_distance(v1.tolist(), v2.tolist())
    print(f" -> Distance between two different people: {dist_diff:.4f} (Expected: > 0.60)")
    assert dist_diff > 0.60, "Different faces matched incorrectly!"
    print(" -> PASS: Tolerance matching accurately distinguishes same vs different people.")

    # 3. Test Database Student Enrollment
    print("\n[Test 3] Testing Student Registration in Database...")
    sample_roll = "21CS042"
    sample_name = "Shashank Uttam"
    db.add_student(
        name=sample_name,
        roll_no=sample_roll,
        face_encoding=v1.tolist(),
        photo_path="data/student_photos/21CS042.jpg",
        department="Computer Science & Engineering"
    )

    student = db.get_student_by_roll(sample_roll)
    assert student is not None, "Failed to retrieve enrolled student from database!"
    assert student["name"] == sample_name, f"Expected {sample_name}, got {student['name']}"
    assert len(student["face_encoding"]) == 128, f"Expected 128-d vector, got {len(student['face_encoding'])}"
    print(f" -> PASS: Student '{sample_name}' successfully enrolled with 128-d biometric vector.")

    # 4. Test Attendance Punch-in
    print("\n[Test 4] Testing Attendance Punch-in & Geofence Recording...")
    punch_result = db.record_attendance(
        roll_no=sample_roll,
        student_name=sample_name,
        room_id="IERT_Room_302",
        confidence=dist_shifted,
        rssi=-62
    )
    print(" -> Punch result:", punch_result)
    assert punch_result["status"] in ["Present", "Already Marked"]

    # Immediate second punch should show already marked
    second_punch = db.record_attendance(
        roll_no=sample_roll,
        student_name=sample_name,
        room_id="IERT_Room_302",
        confidence=dist_shifted,
        rssi=-62
    )
    print(" -> Second punch attempt:", second_punch)
    assert second_punch["already_marked"] is True
    print(" -> PASS: Attendance correctly logged and duplicate punch prevented.")

    # 5. Test Automated Excel Report Generation & Email Package
    print("\n[Test 5] Testing Excel (.xlsx) Report Compilation...")
    sample_class = {
        "id": 1,
        "subject_code": "CS-302",
        "subject_name": "Operating Systems & IoT",
        "teacher_name": "Prof. R. K. Sharma",
        "teacher_email": "teacher.cs@iert.ac.in",
        "room_id": "IERT_Room_302",
        "start_time": "10:00",
        "end_time": "11:00"
    }
    report_file = scheduler.process_class_end(sample_class)
    assert os.path.exists(report_file), f"Report file was not generated: {report_file}"
    assert os.path.getsize(report_file) > 1000, "Report file is suspiciously small or empty."
    print(f" -> PASS: Excel report successfully generated at: {report_file}")
    print(f" -> File Size: {os.path.getsize(report_file)} bytes")

    print("\n==================================================")
    print("  ALL 5 TEST SUITES PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
