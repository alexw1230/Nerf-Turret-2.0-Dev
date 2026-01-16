#include <Servo.h>

Servo servoX;
Servo servoY;

// --------------------
// PIN CONFIG
// --------------------
const int SERVO_X_PIN = 9;
const int SERVO_Y_PIN = 10;

const int RELAY_PIN        = 22;
const int RELAY_INPUT_PIN  = 24;   // NEW INPUT PIN (override)

const int OUTPUT2_PIN      = 23;

// --------------------
// SERVO LIMITS
// --------------------
const int SERVO_MIN = 0;
const int SERVO_MAX = 180;

// --------------------
// STATE
// --------------------
bool relaySerialState = false;  // last serial command for relay

void setup() {
  Serial.begin(115200);

  servoX.attach(SERVO_X_PIN);
  servoY.attach(SERVO_Y_PIN);

  pinMode(RELAY_PIN, OUTPUT);
  pinMode(OUTPUT2_PIN, OUTPUT);

  pinMode(RELAY_INPUT_PIN, INPUT);  // use INPUT_PULLUP if needed

  digitalWrite(RELAY_PIN, LOW);
  digitalWrite(OUTPUT2_PIN, LOW);

  servoX.write(90);
  servoY.write(90);

  Serial.println("Ready");
}

void loop() {

  // --------------------
  // SERIAL COMMANDS
  // --------------------
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    // Relay via serial (0 / 1)
    if (input == "0" || input == "1") {
      relaySerialState = (input == "1");
      return;
    }

    // Second output (2 / 3)
    if (input == "2" || input == "3") {
      digitalWrite(OUTPUT2_PIN, input == "3" ? HIGH : LOW);
      return;
    }

    // Servo command X,Y
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

  // --------------------
  // RELAY OVERRIDE LOGIC
  // --------------------
  bool relayInputState = digitalRead(RELAY_INPUT_PIN);

  // Relay ON if input pin HIGH OR serial says ON
  bool relayFinalState = relayInputState || relaySerialState;

  digitalWrite(RELAY_PIN, relayFinalState ? HIGH : LOW);
}
