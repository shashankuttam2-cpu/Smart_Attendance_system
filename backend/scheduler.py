import os
import time
import asyncio
import smtplib
import pandas as pd
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, Dict, Any, List

from config import settings
from database import db

class ReportScheduler:
    def __init__(self):
        self.is_running = False
        self.last_reported_classes = set() # Avoid sending duplicate reports for the same class in one day

    def generate_excel_report(self, class_info: Dict[str, Any], attendance_records: List[Dict[str, Any]]) -> str:
        """
        Creates a styled Excel spreadsheet (.xlsx) for the class session attendance.
        Returns the absolute filepath of the generated spreadsheet.
        """
        today_str = date.today().isoformat()
        subject_code = class_info.get("subject_code", "GEN")
        room_id = class_info.get("room_id", settings.DEFAULT_ROOM_ID)

        filename = f"Attendance_{subject_code}_{room_id}_{today_str}_{datetime.now().strftime('%H%M%S')}.xlsx"
        report_path = os.path.join(settings.REPORTS_DIR, filename)

        # Prepare dataset
        data_rows = []
        for idx, rec in enumerate(attendance_records, 1):
            data_rows.append({
                "S.No": idx,
                "Roll Number": rec.get("roll_no", ""),
                "Student Name": rec.get("student_name", ""),
                "Punch-In Time": rec.get("timestamp", ""),
                "Room / Beacon": rec.get("room_id", ""),
                "Status": rec.get("status", "Present"),
                "AI Verification Score": rec.get("confidence", "N/A"),
                "BLE RSSI (dBm)": rec.get("rssi", "N/A")
            })

        if not data_rows:
            # Empty attendance placeholder
            data_rows.append({
                "S.No": "-",
                "Roll Number": "No Students Recorded",
                "Student Name": "-",
                "Punch-In Time": "-",
                "Room / Beacon": room_id,
                "Status": "Absent",
                "AI Verification Score": "-",
                "BLE RSSI (dBm)": "-"
            })

        df = pd.DataFrame(data_rows)

        # Write to Excel using openpyxl with clean formatting
        with pd.ExcelWriter(report_path, engine="openpyxl") as writer:
            # Metadata sheet
            meta_df = pd.DataFrame([
                {"Field": "Institute", "Value": "Institute of Engineering and Rural Technology (IERT)"},
                {"Field": "Subject Code", "Value": subject_code},
                {"Field": "Subject Name", "Value": class_info.get("subject_name", "")},
                {"Field": "Instructor", "Value": class_info.get("teacher_name", "")},
                {"Field": "Teacher Email", "Value": class_info.get("teacher_email", "")},
                {"Field": "Classroom", "Value": room_id},
                {"Field": "Session Schedule", "Value": f"{class_info.get('start_time')} - {class_info.get('end_time')}"},
                {"Field": "Date", "Value": today_str},
                {"Field": "Total Present", "Value": len(attendance_records) if attendance_records else 0},
                {"Field": "Generated At", "Value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            ])
            meta_df.to_excel(writer, sheet_name="Session Summary", index=False)
            df.to_excel(writer, sheet_name="Attendance Sheet", index=False)

        print(f"[Scheduler] Generated attendance report: {report_path}")
        return report_path

    def send_report_email(
        self, 
        recipient_email: str, 
        subject_name: str, 
        report_file_path: str,
        total_present: int
    ) -> bool:
        """
        Sends the generated .xlsx attendance sheet to the teacher via SMTP.
        Falls back to console simulation if MOCK_EMAIL_DISPATCH is True or credentials missing.
        """
        email_subject = f"[Attendance Report] {subject_name} - {date.today().strftime('%d %b %Y')}"
        email_body = f"""
Dear Faculty Member,

Please find attached the automated facial recognition attendance report for your recent class session.

Class Details:
- Subject: {subject_name}
- Date: {date.today().isoformat()}
- Total Present Students: {total_present}
- Digital Geofence Room: {settings.DEFAULT_ROOM_ID}

This report was automatically compiled by the IERT Smart Attendance System.

Regards,
IERT Automated Attendance Engine
"""
        # If in Mock Mode or credentials are empty, log and succeed without throwing
        if settings.MOCK_EMAIL_DISPATCH or not settings.SMTP_PASSWORD:
            print("=" * 60)
            print("[Scheduler - Mock Email Dispatcher]")
            print(f"To      : {recipient_email}")
            print(f"Subject : {email_subject}")
            print(f"File    : {report_file_path}")
            print(f"Status  : [MOCK MODE] Email packaged successfully. Report saved at {report_file_path}")
            print("=" * 60)
            return True

        try:
            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_USER
            msg["To"] = recipient_email
            msg["Subject"] = email_subject
            msg.attach(MIMEText(email_body, "plain"))

            # Attach Excel File
            with open(report_file_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {os.path.basename(report_file_path)}",
            )
            msg.attach(part)

            # SMTP Server Connection
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, recipient_email, msg.as_string())
            server.quit()

            print(f"[Scheduler] Successfully emailed report to {recipient_email}")
            return True
        except Exception as e:
            print(f"[Scheduler] Failed to send email via SMTP: {e}")
            return False

    def process_class_end(self, class_info: Dict[str, Any]) -> str:
        """Compiles session attendance and sends report to teacher."""
        today_str = date.today().isoformat()
        room_id = class_info.get("room_id", settings.DEFAULT_ROOM_ID)
        
        # Query attendance marked today for this room
        records = db.get_attendance_logs(query_date=today_str, room_id=room_id)
        
        # Generate Excel
        report_path = self.generate_excel_report(class_info, records)
        
        # Dispatch Email
        teacher_email = class_info.get("teacher_email") or settings.DEFAULT_TEACHER_EMAIL
        subject_title = f"{class_info.get('subject_code', '')} {class_info.get('subject_name', '')}"
        
        self.send_report_email(teacher_email, subject_title, report_path, len(records))
        return report_path

    async def run_cron_loop(self):
        """Continuous background timer monitoring the class timetable."""
        self.is_running = True
        print("[Scheduler] Automated Class End Report Daemon started.")

        while self.is_running:
            try:
                now_str = datetime.now().strftime("%H:%M")
                today_str = date.today().isoformat()
                classes = db.get_all_classes()

                for cls in classes:
                    class_key = f"{today_str}_{cls['id']}_{cls['end_time']}"
                    # If current time matches or is right after end_time, trigger report
                    if cls["end_time"] == now_str and class_key not in self.last_reported_classes:
                        print(f"[Scheduler] Class session ended: {cls['subject_code']} at {now_str}. Compiling report...")
                        self.process_class_end(cls)
                        self.last_reported_classes.add(class_key)

            except Exception as e:
                print(f"[Scheduler] Background error: {e}")

            # Check every 30 seconds
            await asyncio.sleep(30)

scheduler = ReportScheduler()
