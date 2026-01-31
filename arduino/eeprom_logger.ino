/*
 * UTRA EEPROM Logger
 * TODO: Implement logEvent() and dumpLogs()
 */

#include <EEPROM.h>

void setup() {
  Serial.begin(9600);
}

void loop() {
  // TODO: Implement
}

void logEvent(byte eventCode, byte zoneID) {
  // TODO: Save to EEPROM
}

void dumpLogs() {
  // TODO: Print EEPROM to Serial as JSON
}
