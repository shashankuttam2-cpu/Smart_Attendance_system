# Module 1: Hardware - ESP32 BLE Beacon Setup Guide

## 1. Overview
The ESP32 acts as the **Digital Geofence** for classroom attendance. It continuously broadcasts an invisible Bluetooth Low Energy (BLE) advertisement containing a specific Room Identifier (`IERT_Room_302`) and UUID (`4fafc201-1fb5-459e-8fcc-c5c9c331914b`).

- **No Wi-Fi or Internet Required**: Operates autonomously on any standard 5V 1A mobile phone charger or power bank.
- **Physical Placement**: Mounted near the whiteboard or centered on the classroom ceiling for uniform omnidirectional coverage.
- **Controlled Geofence Range**: Calibrated to approximately 7–10 meters.

---

## 2. Hardware Bill of Materials (BOM)
| Component | Specification | Quantity | Approx Cost |
| :--- | :--- | :--- | :--- |
| **Microcontroller** | ESP32 NodeMCU (ESP-WROOM-32 30-pin / 38-pin) | 1 | $3 - $5 |
| **Power Source** | 5V USB Wall Adapter or 5V Power Bank | 1 | $3 |
| **Cable** | Micro-USB to USB-A data cable | 1 | $1 |
| **Enclosure** | 3D Printed Box or Small Plastic Project Enclosure | 1 | Optional |

---

## 3. Flashing Instructions (Arduino IDE)

### Step 1: Install Arduino IDE & ESP32 Board Package
1. Download and install [Arduino IDE (2.x or 1.8.x)](https://www.arduino.cc/en/software).
2. Open **File** > **Preferences**.
3. In **Additional Boards Manager URLs**, add:
   ```text
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. Open **Tools** > **Board** > **Boards Manager**, search for `esp32` by Espressif Systems, and click **Install**.

### Step 2: Configure Arduino IDE Settings
- **Board**: `ESP32 Dev Module` (or `DOIT ESP32 DEVKIT V1`)
- **Upload Speed**: `921600` (or `115200` if upload fails)
- **CPU Frequency**: `240MHz (WiFi/BT)`
- **Flash Frequency**: `80MHz`
- **Partition Scheme**: `Default 4MB with spiffs (1.2MB APP/1.5MB SPIFFS)`
- **Port**: Select the COM port corresponding to your connected ESP32 (e.g., `COM3`, `COM5`).

### Step 3: Upload the Firmware
1. Open `IERT_BLE_Beacon.ino` in Arduino IDE.
2. Click the **Upload** button (arrow icon).
3. If the console shows `Connecting........_____.....`, press and hold the **BOOT** button on your ESP32 board for 2 seconds until uploading begins.
4. Open the **Serial Monitor** at baud rate **115200** to observe the beacon initialization log:
   ```text
   ==================================================
     IERT Smart Attendance - ESP32 BLE Beacon
   ==================================================
   Room Name     : IERT_Room_302
   Beacon UUID   : 4fafc201-1fb5-459e-8fcc-c5c9c331914b
   Major / Minor : 1 / 302
   Status        : BLE Beacon is active and broadcasting!
   Range         : ~7-10 meters perimeter (Classroom Geofence Active)
   ==================================================
   ```

---

## 4. Range & Signal Calibration (Tx Power Tuning)

In `IERT_BLE_Beacon.ino`, you can adjust the transmission power according to the classroom size:

```cpp
esp_ble_tx_power_set(ESP_BLE_PWR_TYPE_ADV, ESP_PWR_LVL_N3);
```

| Constant | Tx Power | Approximate Range | Best Suited For |
| :--- | :--- | :--- | :--- |
| `ESP_PWR_LVL_N12` | -12 dBm | 2 – 4 meters | Small seminar/lab desks |
| `ESP_PWR_LVL_N9`  | -9 dBm  | 4 – 6 meters | Compact tutorial room |
| `ESP_PWR_LVL_N6`  | -6 dBm  | 6 – 8 meters | Standard 40-student classroom |
| **`ESP_PWR_LVL_N3`** | **-3 dBm** | **7 – 10 meters** | **Standard 60-student room (Recommended)** |
| `ESP_PWR_LVL_P0`  | 0 dBm   | 10 – 15 meters | Large lecture halls |

### Mobile RSSI Threshold
In the mobile app (Module 3), the default RSSI threshold is set to **`-75 dBm`**.
- When inside the classroom: Signal strength is typically between `-45 dBm` and `-70 dBm` $\rightarrow$ **Allowed**.
- When outside the classroom / in the hallway: Signal strength drops below `-78 dBm` $\rightarrow$ **Error: "Please enter the classroom"**.
