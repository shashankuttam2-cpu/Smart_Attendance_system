import sqlite3
import json
import os
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from config import settings

class Database:
    def __init__(self, db_path: str = settings.DB_PATH):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initializes database schema with Students, Attendance, and Timetable tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Students Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    roll_no TEXT UNIQUE NOT NULL,
                    face_encoding TEXT NOT NULL,
                    photo_path TEXT,
                    department TEXT DEFAULT 'Computer Science',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Attendance Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    roll_no TEXT NOT NULL,
                    student_name TEXT NOT NULL,
                    date TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    room_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Present',
                    confidence REAL,
                    rssi INTEGER,
                    FOREIGN KEY(roll_no) REFERENCES students(roll_no)
                );
            """)

            # Timetable / Classes Table for Auto-Reporting Cron
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS classes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_code TEXT NOT NULL,
                    subject_name TEXT NOT NULL,
                    teacher_name TEXT NOT NULL,
                    teacher_email TEXT NOT NULL,
                    room_id TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL
                );
            """)

            # Seed a default sample class timetable if empty
            cursor.execute("SELECT COUNT(*) FROM classes")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO classes (subject_code, subject_name, teacher_name, teacher_email, room_id, start_time, end_time)
                    VALUES 
                    ('CS-302', 'Operating Systems & IoT', 'Prof. R. K. Sharma', 'teacher.cs@iert.ac.in', 'IERT_Room_302', '10:00', '11:00'),
                    ('CS-304', 'Machine Learning & AI', 'Dr. S. Verma', 'teacher.cs@iert.ac.in', 'IERT_Room_302', '11:15', '12:15');
                """)

            conn.commit()

    # --------------------------------------------------------------------------
    # Student Operations
    # --------------------------------------------------------------------------
    def add_student(self, name: str, roll_no: str, face_encoding: List[float], photo_path: str, department: str = "Computer Science") -> int:
        encoding_json = json.dumps(face_encoding)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO students (name, roll_no, face_encoding, photo_path, department)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(roll_no) DO UPDATE SET
                    name=excluded.name,
                    face_encoding=excluded.face_encoding,
                    photo_path=excluded.photo_path,
                    department=excluded.department;
            """, (name.strip(), roll_no.strip().upper(), encoding_json, photo_path, department))
            conn.commit()
            return cursor.lastrowid

    def get_all_students(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, roll_no, photo_path, department, created_at FROM students ORDER BY roll_no ASC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_student_by_roll(self, roll_no: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students WHERE roll_no = ?", (roll_no.strip().upper(),))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            res["face_encoding"] = json.loads(res["face_encoding"])
            return res

    def get_all_student_encodings(self) -> List[Dict[str, Any]]:
        """Returns student roll_no, name, and parsed 128-d face encodings for matching."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, roll_no, face_encoding FROM students")
            rows = cursor.fetchall()
            results = []
            for r in rows:
                results.append({
                    "id": r["id"],
                    "name": r["name"],
                    "roll_no": r["roll_no"],
                    "face_encoding": json.loads(r["face_encoding"])
                })
            return results

    # --------------------------------------------------------------------------
    # Attendance Operations
    # --------------------------------------------------------------------------
    def record_attendance(self, roll_no: str, student_name: str, room_id: str, confidence: float, rssi: int = None) -> Dict[str, Any]:
        today_str = date.today().isoformat()
        now_dt = datetime.now()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if student is already marked present today for this room
            cursor.execute("""
                SELECT id, timestamp FROM attendance 
                WHERE roll_no = ? AND date = ? AND room_id = ?
            """, (roll_no, today_str, room_id))
            existing = cursor.fetchone()
            
            if existing:
                return {
                    "status": "Already Marked",
                    "already_marked": True,
                    "recorded_time": existing["timestamp"],
                    "roll_no": roll_no,
                    "student_name": student_name,
                    "room_id": room_id
                }

            cursor.execute("""
                INSERT INTO attendance (roll_no, student_name, date, timestamp, room_id, status, confidence, rssi)
                VALUES (?, ?, ?, ?, ?, 'Present', ?, ?)
            """, (roll_no, student_name, today_str, now_dt.strftime("%Y-%m-%d %H:%M:%S"), room_id, round(confidence, 4), rssi))
            conn.commit()

            return {
                "status": "Present",
                "already_marked": False,
                "recorded_time": now_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "roll_no": roll_no,
                "student_name": student_name,
                "room_id": room_id,
                "confidence": round(confidence, 4)
            }

    def get_attendance_logs(self, query_date: Optional[str] = None, room_id: Optional[str] = None) -> List[Dict[str, Any]]:
        target_date = query_date or date.today().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if room_id:
                cursor.execute("""
                    SELECT id, roll_no, student_name, date, timestamp, room_id, status, confidence, rssi 
                    FROM attendance 
                    WHERE date = ? AND room_id = ? 
                    ORDER BY timestamp DESC
                """, (target_date, room_id))
            else:
                cursor.execute("""
                    SELECT id, roll_no, student_name, date, timestamp, room_id, status, confidence, rssi 
                    FROM attendance 
                    WHERE date = ? 
                    ORDER BY timestamp DESC
                """, (target_date,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_active_class(self, current_time_str: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Returns the currently active scheduled class session."""
        now_time = current_time_str or datetime.now().strftime("%H:%M")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM classes 
                WHERE ? >= start_time AND ? <= end_time
                LIMIT 1
            """, (now_time, now_time))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_classes(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM classes ORDER BY start_time ASC")
            return [dict(r) for r in cursor.fetchall()]

db = Database()
