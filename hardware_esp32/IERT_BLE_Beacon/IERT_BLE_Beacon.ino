/*
 * =====================================================================================
 *  IERT Smart Attendance System - Module 1: Digital Geofence BLE Beacon
 *  Target Hardware : ESP32 Microcontroller (NodeMCU ESP32 / ESP32 WROOM / ESP32-CAM)
 *  Framework       : Arduino IDE (ESP32 BLE Library by Neil Kolban / Espressif)
 * =====================================================================================
 *  Working Principle:
 *  - Continuous non-connectable BLE advertising.
 *  - Broadcasts unique Classroom UUID, Major/Minor identifier, and Room Name.
 *  - Transmission power tuned to ESP_PWR_LVL_N3 / ESP_PWR_LVL_N6 for a controlled 
 *    5-10 meter classroom perimeter (preventing signal leakage into corridors).
 *  - No Wi-Fi or Internet required. Operates immediately upon receiving 5V USB power.
 * =====================================================================================
 */

#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <BLEBeacon.h>
#include "esp_bt_main.h"
#include "esp_bt_device.h"

// -----------------------------------------------------------------------------
// Beacon Configuration
// -----------------------------------------------------------------------------
#define DEVICE_NAME         "IERT_Room_302"
// Standard 128-bit UUID for Room 302 geofence
#define BEACON_UUID         "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define BEACON_MAJOR        1           // Building / Block 1
#define BEACON_MINOR        302         // Room 302
#define LED_PIN             2           // On-board LED indicator (GPIO 2 on most ESP32 boards)

// Measured RSSI at 1 meter distance in dBm (used by mobile app for distance estimation)
#define MEASURED_POWER_1M   -59 

// -----------------------------------------------------------------------------
// Global BLE Objects
// -----------------------------------------------------------------------------
BLEAdvertising *pAdvertising;

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH); // Turn on status LED

  Serial.println();
  Serial.println("==================================================");
  Serial.println("  IERT Smart Attendance - ESP32 BLE Beacon");
  Serial.println("==================================================");
  Serial.printf("Room Name     : %s\n", DEVICE_NAME);
  Serial.printf("Beacon UUID   : %s\n", BEACON_UUID);
  Serial.printf("Major / Minor : %d / %d\n", BEACON_MAJOR, BEACON_MINOR);
  Serial.println("Status        : Initializing Bluetooth Low Energy...");

  // 1. Initialize BLE Stack
  BLEDevice::init(DEVICE_NAME);

  // 2. Set Transmission Power for 5 - 10m range
  // Options: ESP_PWR_LVL_N12 (-12dBm), ESP_PWR_LVL_N9 (-9dBm), ESP_PWR_LVL_N6 (-6dBm),
  //          ESP_PWR_LVL_N3 (-3dBm),  ESP_PWR_LVL_P0 (0dBm),   ESP_PWR_LVL_P3 (+3dBm)
  // ESP_PWR_LVL_N3 or ESP_PWR_LVL_P0 gives an optimal ~7-10 meter indoor envelope.
  esp_ble_tx_power_set(ESP_BLE_PWR_TYPE_ADV, ESP_PWR_LVL_N3);

  // 3. Configure iBeacon Data Payload
  BLEBeacon myBeacon;
  myBeacon.setManufacturerId(0x4C00); // Apple iBeacon signature format (universally scanned by iOS/Android)
  
  BLEUUID bleUuid(BEACON_UUID);
  myBeacon.setProximityUUID(bleUuid);
  myBeacon.setMajor(BEACON_MAJOR);
  myBeacon.setMinor(BEACON_MINOR);
  myBeacon.setSignalPower(MEASURED_POWER_1M);

  // 4. Set Advertisement Data
  BLEAdvertisementData advertisementData;
  advertisementData.setFlags(0x04); // BR_EDR_NOT_SUPPORTED
  advertisementData.setName(DEVICE_NAME);

  // Pack the beacon data string
  std::string beaconData = myBeacon.getData();
  advertisementData.setManufacturerData(beaconData);

  // 5. Configure Advertising Parameters
  pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->setAdvertisementData(advertisementData);

  // Scan response data (enables scanner to read the complete device name)
  BLEAdvertisementData scanResponseData;
  scanResponseData.setName(DEVICE_NAME);
  pAdvertising->setScanResponseData(scanResponseData);

  // Broadcast interval: 1 second (1600 units * 0.625ms = 1000ms)
  pAdvertising->setMinInterval(0x0640); 
  pAdvertising->setMaxInterval(0x0640);

  // 6. Start Advertising
  pAdvertising->start();
  Serial.println("Status        : BLE Beacon is active and broadcasting!");
  Serial.println("Range         : ~7-10 meters perimeter (Classroom Geofence Active)");
  Serial.println("==================================================");
}

void loop() {
  // Heartbeat pulse on LED to show active operation
  digitalWrite(LED_PIN, HIGH);
  delay(100);
  digitalWrite(LED_PIN, LOW);
  delay(900);
}
