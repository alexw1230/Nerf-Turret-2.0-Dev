#include <Servo.h>

Servo servoX;
Servo servoY;

// --------------------
// PIN CONFIG
// --------------------
const int SERVO_X_PIN = 9;
const int SERVO_Y_PIN = 10;
const int RELAY_PIN   = 22;

// --------------------
// SERVO LIMITS
// --------------------
const int SERVO_MIN = 0;
const int SERVO_MAX = 180;

void setup() {
  Serial.begin(115200);

  servoX.attach(SERVO_X_PIN);
  servoY.attach(SERVO_Y_PIN);

  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);

  // Center servos
  servoX.write(90);
  servoY.write(90);

  Serial.println("Ready");
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    // --------------------
    // RELAY COMMAND
    // --------------------
    if (input == "0" || input == "1") {
      digitalWrite(RELAY_PIN, input == "1" ? HIGH : LOW);
      return;
    }

    // --------------------
    // SERVO COMMAND X,Y
    // --------------------
    int commaIndex = input.indexOf(',');

    if (commaIndex > 0) {
      int x = input.substring(0, commaIndex).toInt();
      int y = input.substring(commaIndex + 1).toInt();

      x = constrain(x, SERVO_MIN, SERVO_MAX);
      y = constrain(y, SERVO_MIN, SERVO_MAX);

      servoX.write(x);
      servoY.write(y);
    }
  }
}
