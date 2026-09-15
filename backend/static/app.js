/**
 * IERT Smart Attendance System - Frontend Logic & Simulator Controller
 */

// State Management
const state = {
  activeTab: 'liveFeedTab',
  cameraStream: null,
  simImageBlob: null,
  students: [],
  attendance: [],
  classes: [],
  defaultRoomId: 'IERT_Room_302',
  defaultBeaconUuid: '4fafc201-1fb5-459e-8fcc-c5c9c331914b'
};

// DOM Elements
const elements = {
  tabBtns: document.querySelectorAll('.tab-btn'),
  tabPanes: document.querySelectorAll('.tab-pane'),
  toastContainer: document.getElementById('toastContainer'),
  // Stats
  statEnrolled: document.getElementById('statEnrolled'),
  statPresent: document.getElementById('statPresent'),
  attendanceTableBody: document.getElementById('attendanceTableBody'),
  refreshLogsBtn: document.getElementById('refreshLogsBtn'),
  quickExportBtn: document.getElementById('quickExportBtn'),
  // Simulator
  simVideo: document.getElementById('simVideo'),
  simCanvas: document.getElementById('simCanvas'),
  simMarkBtn: document.getElementById('simMarkBtn'),
  startCameraBtn: document.getElementById('startCameraBtn'),
  simUploadFile: document.getElementById('simUploadFile'),
  simUploadBtn: document.getElementById('simUploadBtn'),
  phoneResultCard: document.getElementById('phoneResultCard'),
  dismissResultBtn: document.getElementById('dismissResultBtn'),
  resultIcon: document.getElementById('resultIcon'),
  resultTitle: document.getElementById('resultTitle'),
  resultStudent: document.getElementById('resultStudent'),
  resultMeta: document.getElementById('resultMeta'),
  simRangeBadge: document.getElementById('simRangeBadge'),
  phoneTime: document.getElementById('phoneTime'),
  // Register
  registerForm: document.getElementById('registerForm'),
  regName: document.getElementById('regName'),
  regRoll: document.getElementById('regRoll'),
  regDept: document.getElementById('regDept'),
  regDropzone: document.getElementById('regDropzone'),
  regPhotoInput: document.getElementById('regPhotoInput'),
  dropzonePrompt: document.getElementById('dropzonePrompt'),
  regPhotoPreview: document.getElementById('regPhotoPreview'),
  regWebcamSnapBtn: document.getElementById('regWebcamSnapBtn'),
  regSubmitBtn: document.getElementById('regSubmitBtn'),
  studentListContainer: document.getElementById('studentListContainer'),
  regCountLabel: document.getElementById('regCountLabel'),
  // Reports
  classesList: document.getElementById('classesList'),
  manualReportBtn: document.getElementById('manualReportBtn'),
  reportResultBox: document.getElementById('reportResultBox'),
  reportResultText: document.getElementById('reportResultText'),
  reportDownloadLink: document.getElementById('reportDownloadLink')
};

// -----------------------------------------------------------------------------
// Toast Notifications
// -----------------------------------------------------------------------------
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerText = message;
  elements.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

// -----------------------------------------------------------------------------
// Navigation Tabs
// -----------------------------------------------------------------------------
elements.tabBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    const targetTab = btn.dataset.tab;
    elements.tabBtns.forEach(b => b.classList.remove('active'));
    elements.tabPanes.forEach(p => p.classList.remove('active'));

    btn.classList.add('active');
    document.getElementById(targetTab).classList.add('active');
    state.activeTab = targetTab;

    if (targetTab === 'mobileSimulatorTab' && !state.cameraStream) {
      initWebcam();
    }
  });
});

// -----------------------------------------------------------------------------
// Clock in Virtual Phone
// -----------------------------------------------------------------------------
function updatePhoneClock() {
  const now = new Date();
  elements.phoneTime.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
setInterval(updatePhoneClock, 1000);
updatePhoneClock();

// -----------------------------------------------------------------------------
// Webcam Handling
// -----------------------------------------------------------------------------
async function initWebcam() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
      audio: false
    });
    state.cameraStream = stream;
    elements.simVideo.srcObject = stream;
    showToast('Webcam connected for attendance scanning', 'success');
  } catch (err) {
    console.warn('Webcam not accessible:', err);
    showToast('Webcam not accessible. You can upload an image file instead.', 'warning');
  }
}

elements.startCameraBtn.addEventListener('click', () => initWebcam());

elements.simUploadBtn.addEventListener('click', () => elements.simUploadFile.click());
elements.simUploadFile.addEventListener('change', (e) => {
  if (e.target.files && e.target.files[0]) {
    const file = e.target.files[0];
    state.simImageBlob = file;
    // Render onto video or canvas placeholder
    const reader = new FileReader();
    reader.onload = (evt) => {
      // Create a background preview on video element
      elements.simVideo.srcObject = null;
      elements.simVideo.poster = evt.target.result;
      showToast(`Selected test image: ${file.name}`, 'info');
    };
    reader.readAsDataURL(file);
  }
});

// Capture frame from webcam into Blob
function captureSimFrame() {
  return new Promise((resolve, reject) => {
    if (state.simImageBlob) {
      resolve(state.simImageBlob);
      return;
    }

    if (!state.cameraStream && !elements.simVideo.videoWidth) {
      reject(new Error('Please start the webcam or select an image file first.'));
      return;
    }

    const canvas = elements.simCanvas;
    canvas.width = elements.simVideo.videoWidth || 640;
    canvas.height = elements.simVideo.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(elements.simVideo, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
      if (blob) resolve(blob);
      else reject(new Error('Failed to capture frame from webcam.'));
    }, 'image/jpeg', 0.92);
  });
}

// -----------------------------------------------------------------------------
// Mobile Simulator Attendance Mark Logic (Module 3 Simulation)
// -----------------------------------------------------------------------------
elements.simMarkBtn.addEventListener('click', async () => {
  // 1. Read simulation radio choice
  const rssiChoice = document.querySelector('input[name="rssiSimulation"]:checked').value;

  if (rssiChoice === 'none') {
    showResultPopup(false, 'Out of Range', 'No Classroom Beacon Found', 'Error: IERT_Room_302 beacon not detected nearby.');
    return;
  }

  const rssiValue = parseInt(rssiChoice, 10);

  // Update simulator UI badge
  if (rssiValue < -75) {
    elements.simRangeBadge.innerHTML = `<span class="pulse-dot red"></span> Weak Signal (${rssiValue} dBm)`;
  } else {
    elements.simRangeBadge.innerHTML = `<span class="pulse-dot green"></span> Inside Room 302 (${rssiValue} dBm)`;
  }

  // Disable button during scan & upload
  elements.simMarkBtn.disabled = true;
  elements.simMarkBtn.innerHTML = 'Scanning & Verifying...';

  try {
    const imageBlob = await captureSimFrame();

    const formData = new FormData();
    formData.append('photo', imageBlob, 'live_selfie.jpg');
    formData.append('room_id', state.defaultRoomId);
    formData.append('beacon_uuid', state.defaultBeaconUuid);
    formData.append('rssi', rssiValue);

    const response = await fetch('/api/v1/verify', {
      method: 'POST',
      body: formData
    });

    const data = await response.json();

    if (response.ok && data.success) {
      const already = data.already_marked ? ' (Already Punched)' : '';
      showResultPopup(
        true,
        `Attendance Marked!${already}`,
        `${data.student_name} (${data.roll_no})`,
        `Room 302 • Confidence: ${data.match_confidence} • Signal: ${rssiValue} dBm`
      );
      playChime(true);
      fetchAttendance(); // Refresh table immediately
      fetchSystemStatus();
    } else {
      const errMsg = data.detail || data.message || 'Verification failed';
      showResultPopup(false, 'Verification Failed', errMsg, `Signal: ${rssiValue} dBm`);
      playChime(false);
    }
  } catch (err) {
    showResultPopup(false, 'Connection Error', err.message, 'Make sure camera is active');
    playChime(false);
  } finally {
    elements.simMarkBtn.disabled = false;
    elements.simMarkBtn.innerHTML = `
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
      Mark Attendance
    `;
  }
});

function showResultPopup(isSuccess, title, student, meta) {
  elements.resultIcon.className = isSuccess ? 'result-icon' : 'result-icon error';
  elements.resultIcon.textContent = isSuccess ? '✓' : '✕';
  elements.resultTitle.textContent = title;
  elements.resultStudent.textContent = student;
  elements.resultMeta.textContent = meta;
  elements.phoneResultCard.style.display = 'flex';
}

elements.dismissResultBtn.addEventListener('click', () => {
  elements.phoneResultCard.style.display = 'none';
});

// Audio feedback chime using Web Audio API (no external sound files required)
function playChime(success) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);

    if (success) {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
      osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.15); // A5
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
      osc.start();
      osc.stop(ctx.currentTime + 0.35);
    } else {
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(220, ctx.currentTime);
      osc.frequency.setValueAtTime(160, ctx.currentTime + 0.1);
      gain.gain.setValueAtTime(0.2, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
      osc.start();
      osc.stop(ctx.currentTime + 0.3);
    }
  } catch (e) {
    // AudioContext blocked by browser policy
  }
}

// -----------------------------------------------------------------------------
// Student Registration (Admin Flow)
// -----------------------------------------------------------------------------
elements.regDropzone.addEventListener('click', () => elements.regPhotoInput.click());

elements.regPhotoInput.addEventListener('change', (e) => {
  if (e.target.files && e.target.files[0]) {
    const file = e.target.files[0];
    const reader = new FileReader();
    reader.onload = (evt) => {
      elements.regPhotoPreview.src = evt.target.result;
      elements.regPhotoPreview.style.display = 'block';
      elements.dropzonePrompt.style.display = 'none';
    };
    reader.readAsDataURL(file);
  }
});

// Snap from webcam for registration
elements.regWebcamSnapBtn.addEventListener('click', async () => {
  try {
    const imageBlob = await captureSimFrame();
    const reader = new FileReader();
    reader.onload = (evt) => {
      elements.regPhotoPreview.src = evt.target.result;
      elements.regPhotoPreview.style.display = 'block';
      elements.dropzonePrompt.style.display = 'none';
    };
    reader.readAsDataURL(imageBlob);

    // Populate file input with the snapped blob
    const file = new File([imageBlob], "snap_selfie.jpg", { type: "image/jpeg" });
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    elements.regPhotoInput.files = dataTransfer.files;

    showToast('Captured photo from webcam for registration!', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
});

elements.registerForm.addEventListener('submit', async (e) => {
  e.preventDefault();

  if (!elements.regPhotoInput.files || elements.regPhotoInput.files.length === 0) {
    showToast('Please select or snap a photo of the student.', 'error');
    return;
  }

  const formData = new FormData();
  formData.append('name', elements.regName.value);
  formData.append('roll_no', elements.regRoll.value);
  formData.append('department', elements.regDept.value);
  formData.append('photo', elements.regPhotoInput.files[0]);

  elements.regSubmitBtn.disabled = true;
  elements.regSubmitBtn.innerHTML = 'Extracting AI Features...';

  try {
    const response = await fetch('/api/v1/register', {
      method: 'POST',
      body: formData
    });

    const data = await response.json();

    if (response.ok && data.success) {
      showToast(data.message, 'success');
      elements.registerForm.reset();
      elements.regPhotoPreview.style.display = 'none';
      elements.dropzonePrompt.style.display = 'block';
      fetchStudents();
      fetchSystemStatus();
    } else {
      const err = data.detail || data.message || 'Registration failed';
      showToast(`Error: ${err}`, 'error');
    }
  } catch (err) {
    showToast(`Network error: ${err.message}`, 'error');
  } finally {
    elements.regSubmitBtn.disabled = false;
    elements.regSubmitBtn.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
      Extract Features &amp; Register Student
    `;
  }
});

// -----------------------------------------------------------------------------
// Data Fetching & Table Rendering
// -----------------------------------------------------------------------------
async function fetchSystemStatus() {
  try {
    const res = await fetch('/api/v1/system/status');
    const data = await res.json();
    if (res.ok) {
      elements.statEnrolled.textContent = data.statistics.total_students_enrolled;
      elements.statPresent.textContent = data.statistics.today_attendance_count;
    }
  } catch (e) {
    console.warn('Status fetch error:', e);
  }
}

async function fetchStudents() {
  try {
    const res = await fetch('/api/v1/students');
    const list = await res.json();
    state.students = list;
    elements.regCountLabel.textContent = `${list.length} Enrolled Student${list.length === 1 ? '' : 's'}`;

    if (list.length === 0) {
      elements.studentListContainer.innerHTML = '<div class="empty-state">No students enrolled yet. Add the first student using the form.</div>';
      return;
    }

    elements.studentListContainer.innerHTML = list.map(s => `
      <div class="student-card">
        <div class="student-avatar">${s.name.substring(0, 2).toUpperCase()}</div>
        <div class="student-info">
          <div class="student-name">${s.name}</div>
          <div class="student-meta">${s.roll_no} • ${s.department}</div>
        </div>
      </div>
    `).join('');
  } catch (e) {
    console.warn('Students fetch error:', e);
  }
}

async function fetchAttendance() {
  try {
    const res = await fetch('/api/v1/attendance');
    const data = await res.json();
    const records = data.records || [];
    state.attendance = records;

    if (records.length === 0) {
      elements.attendanceTableBody.innerHTML = `
        <tr>
          <td colspan="7" class="empty-state">No attendance logs recorded yet for today. Use the Mobile Simulator to mark attendance.</td>
        </tr>
      `;
      return;
    }

    elements.attendanceTableBody.innerHTML = records.map(r => {
      const timeStr = r.timestamp.split(' ')[1] || r.timestamp;
      const rssiBadge = r.rssi ? `${r.rssi} dBm` : 'N/A';
      return `
        <tr>
          <td><strong>${timeStr}</strong></td>
          <td><code>${r.roll_no}</code></td>
          <td>${r.student_name}</td>
          <td>${r.room_id}</td>
          <td>${rssiBadge}</td>
          <td>${r.confidence ? r.confidence.toFixed(3) : 'N/A'}</td>
          <td><span class="badge badge-success">✓ ${r.status}</span></td>
        </tr>
      `;
    }).join('');
  } catch (e) {
    console.warn('Attendance fetch error:', e);
  }
}

async function fetchClasses() {
  try {
    const res = await fetch('/api/v1/classes');
    const list = await res.json();
    state.classes = list;

    elements.classesList.innerHTML = list.map(c => `
      <div class="class-card">
        <div>
          <div class="class-title">${c.subject_code} - ${c.subject_name}</div>
          <div class="class-schedule">${c.start_time} to ${c.end_time} • ${c.room_id}</div>
          <div class="class-instructor">Faculty: ${c.teacher_name} (${c.teacher_email})</div>
        </div>
        <button class="btn btn-sm btn-outline trigger-class-report" data-id="${c.id}">
          Send Report Email
        </button>
      </div>
    `).join('');

    // Attach listeners to trigger report buttons
    document.querySelectorAll('.trigger-class-report').forEach(btn => {
      btn.addEventListener('click', () => triggerClassReport(btn.dataset.id));
    });
  } catch (e) {
    console.warn('Classes fetch error:', e);
  }
}

async function triggerClassReport(classId = null) {
  const formData = new FormData();
  if (classId) formData.append('class_id', classId);

  try {
    const res = await fetch('/api/v1/report/generate', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();

    if (res.ok && data.success) {
      showToast(data.message, 'success');
      elements.reportResultBox.style.display = 'flex';
      elements.reportResultText.textContent = data.file_name;
      elements.reportDownloadLink.href = data.download_url;
      elements.reportDownloadLink.setAttribute('download', data.file_name);
    } else {
      showToast(data.detail || 'Report generation failed', 'error');
    }
  } catch (e) {
    showToast(`Error: ${e.message}`, 'error');
  }
}

elements.manualReportBtn.addEventListener('click', () => triggerClassReport());
elements.quickExportBtn.addEventListener('click', () => triggerClassReport());
elements.refreshLogsBtn.addEventListener('click', () => {
  fetchAttendance();
  fetchSystemStatus();
  showToast('Attendance logs updated', 'info');
});

// Initial boot
fetchSystemStatus();
fetchStudents();
fetchAttendance();
fetchClasses();

// Periodic Auto-refresh for live classroom display (every 4 seconds)
setInterval(() => {
  if (state.activeTab === 'liveFeedTab') {
    fetchAttendance();
    fetchSystemStatus();
  }
}, 4000);

