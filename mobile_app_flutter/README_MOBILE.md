# Module 3: Frontend - Mobile App Setup & Build Guide

## 1. Overview
The **IERT Smart Attendance Mobile App** is built using Flutter for cross-platform Android and iOS deployment.

### Key Working Principles:
1. **Prominent UI**: Displays a central **"Mark Attendance"** button.
2. **Invisible BLE Geofence Check**: Silently scans for `IERT_Room_302` beacon UUID (`4fafc201-1fb5-459e-8fcc-c5c9c331914b`).
3. **Signal Strength (RSSI) Filter**:
   - If RSSI is $\ge -75\text{ dBm}$ $\rightarrow$ Student is physically inside the classroom $\rightarrow$ Proceed.
   - If RSSI is $< -75\text{ dBm}$ $\rightarrow$ Student is in the hallway/corridor $\rightarrow$ Error: *"Please enter the classroom."*
4. **Privacy-Preserving Facial Capture**: Opens the front camera in-memory, captures the face, and streams directly to `/api/v1/verify` via HTTP Multipart without saving to the phone's gallery.

---

## 2. Platform Permissions Configuration

### Android Configuration (`android/app/src/main/AndroidManifest.xml`)
Add the following permissions inside the `<manifest>` tag:

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <!-- Camera Permission -->
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-feature android:name="android.hardware.camera" android:required="false" />
    <uses-feature android:name="android.hardware.camera.autofocus" android:required="false" />

    <!-- Bluetooth Low Energy (Android 12+) -->
    <uses-permission android:name="android.permission.BLUETOOTH_SCAN" 
                     android:usesPermissionFlags="neverForLocation" />
    <uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />

    <!-- Legacy Bluetooth & Location (Android 11 and lower) -->
    <uses-permission android:name="android.permission.BLUETOOTH" android:maxSdkVersion="30" />
    <uses-permission android:name="android.permission.BLUETOOTH_ADMIN" android:maxSdkVersion="30" />
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />

    <!-- Internet -->
    <uses-permission android:name="android.permission.INTERNET" />

    <application ...
        android:usesCleartextTraffic="true">
        ...
    </application>
</manifest>
```

In `android/app/build.gradle`, ensure `minSdkVersion` is at least **21** (required for camera and BLE).

### iOS Configuration (`ios/Runner/Info.plist`)
Add the following permission keys inside `<dict>`:

```xml
<key>NSCameraUsageDescription</key>
<string>This app requires camera access to verify student facial attendance inside the classroom.</string>
<key>NSBluetoothAlwaysUsageDescription</key>
<string>This app scans for the classroom BLE beacon to verify your physical presence in Room 302.</string>
<key>NSBluetoothPeripheralUsageDescription</key>
<string>This app scans for classroom geofence beacons.</string>
<key>NSLocationWhenInUseUsageDescription</key>
<string>Location access is required by iOS to perform Bluetooth beacon distance measurements.</string>
```

---

## 3. Connecting to the Backend Server

In `lib/services/api_service.dart`:
```dart
// For Android Emulator (maps to host localhost):
static String baseUrl = "http://10.0.2.2:8000/api/v1";

// For Physical Phone over Wi-Fi (replace with your laptop's Wi-Fi IP address):
// static String baseUrl = "http://192.168.1.15:8000/api/v1";
```

---

## 4. How to Run the App

1. Connect your Android or iOS smartphone via USB or launch an emulator.
2. Navigate to the `mobile_app_flutter` directory:
   ```bash
   cd mobile_app_flutter
   ```
3. Install dependencies:
   ```bash
   flutter pub get
   ```
4. Launch the application:
   ```bash
   flutter run
   ```

---

## 5. Instant Browser Simulation (No Flutter Build Needed)
If you do not have Flutter installed on your computer yet, you can test the **exact same mobile attendance experience** using our built-in **Web Simulator**:
1. Run the Python backend: `python backend/main.py`
2. Open your browser at `http://localhost:8000`
3. Click the **"Student Mobile Simulator"** tab.
4. Toggle RSSI between **"Inside Classroom"** and **"Outside Corridor"**, snap your face using your webcam, and click **"Mark Attendance"**!
