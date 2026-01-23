//Turret servo & fire control

#include <Servo.h>

//Init servos
Servo servoX;
Servo servoY;

//Pin assign
const int SERVO_X_PIN = 9;
const int SERVO_Y_PIN = 10;

const int RELAY_PIN = 22;
const int RELAY_INPUT_PIN = 24;

const int OUTPUT2_PIN = 23;

//Servo limits
const int SERVO_MIN = 0;
const int SERVO_MAX = 180;

//Relay state
bool relaySerialState = false;

//Setup serial, servos, outputs
void setup() {
  Serial.begin(115200);

  servoX.attach(SERVO_X_PIN);
  servoY.attach(SERVO_Y_PIN);

  pinMode(RELAY_PIN, OUTPUT);
  pinMode(OUTPUT2_PIN, OUTPUT);

  pinMode(RELAY_INPUT_PIN, INPUT);

  digitalWrite(RELAY_PIN, LOW);
  digitalWrite(OUTPUT2_PIN, LOW);

  //Center servos
  servoX.write(90);
  servoY.write(90);

}

//Main
void loop() {

  if (Serial.available()) { //Command handle
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input == "0" || input == "1") { //Fire control
      relaySerialState = (input == "1");
      return;
    }

    if (input == "2" || input == "3") { //Tracking
      digitalWrite(OUTPUT2_PIN, input == "3" ? HIGH : LOW);
      return;
    }
    //Servo movement parse
    int commaIndex = input.indexOf(',');
    if (commaIndex > 0) {
      int x = input.substring(0, commaIndex).toInt();
      int y = input.substring(commaIndex + 1).toInt();

      x = constrain(x, SERVO_MIN, SERVO_MAX);
      y = constrain(y, SERVO_MIN, SERVO_MAX);
      //Write to servo
      servoX.write(x);
      servoY.write(y);
    }
  }

  //Fire override handling
  bool relayInputState = digitalRead(RELAY_INPUT_PIN);

  bool relayFinalState = relayInputState || relaySerialState;

  digitalWrite(RELAY_PIN, relayFinalState ? HIGH : LOW);
}
