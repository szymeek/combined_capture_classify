// USB mode >> USB-OTG(TinyUSB)

#include "USB.h"
#include "USBHIDKeyboard.h"

USBHIDKeyboard Keyboard;

void setup() {
  // Start USB as composite device (CDC + HID)
  USB.begin();
  Keyboard.begin();
  
  // Open CDC serial for commands from PC
  Serial.begin(115200);
  Serial.println("ESP32-S3 HID Keyboard Ready");
  Serial.println("Commands: ALT, Q, E");
  
  // Initialize random seed using analog noise
  randomSeed(analogRead(0) + micros());
}

int getRandomKeyDelay() {
  // Generate random delay between 90-191ms
  return random(90, 191); // random(min, max) where max is exclusive
}

void pressLeftAlt() {
  int holdTime = getRandomKeyDelay();
  Keyboard.press(KEY_LEFT_ALT);
  delay(holdTime);
  Keyboard.release(KEY_LEFT_ALT);
  Serial.print("Pressed Left Alt for ");
  Serial.print(holdTime);
  Serial.println("ms");
}

void pressQ() {
  int holdTime = getRandomKeyDelay();
  Keyboard.press('q');
  delay(holdTime);
  Keyboard.release('q');
  Serial.print("Pressed Q for ");
  Serial.print(holdTime);
  Serial.println("ms");
}

void pressE() {
  int holdTime = getRandomKeyDelay();
  Keyboard.press('e');
  delay(holdTime);
  Keyboard.release('e');
  Serial.print("Pressed E for ");
  Serial.print(holdTime);
  Serial.println("ms");
}

void loop() {
  // Check for commands on CDC
  static String buf;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (buf.length()) {
        String cmd = buf;
        buf = "";
        cmd.trim();
        cmd.toUpperCase();
        
        if (cmd == "ALT") {
          pressLeftAlt();
        } else if (cmd == "Q") {
          pressQ();
        } else if (cmd == "E") {
          pressE();
        } else {
          Serial.print("Unknown command: ");
          Serial.println(cmd);
          Serial.println("Valid commands: ALT, Q, E");
        }
      }
    } else {
      buf += c;
      // Avoid runaway memory on long noise
      if (buf.length() > 128) buf = "";
    }
  }
  delay(5);
}
