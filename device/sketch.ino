const int SERVO_PIN = 18;
const int SERVO_FREQ = 50;
const int SERVO_RES = 14;   // 14 бит

void servoAttach() {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcAttach(SERVO_PIN, SERVO_FREQ, SERVO_RES);
#else
  ledcSetup(0, SERVO_FREQ, SERVO_RES);
  ledcAttachPin(SERVO_PIN, 0);
#endif
}

void servoWrite(int angle) {
  if (angle < 0) angle = 0;
  if (angle > 180) angle = 180;
  int pulseUs = map(angle, 0, 180, 500, 2400);
  uint32_t duty = (uint32_t)pulseUs * ((1 << SERVO_RES) - 1) / 20000;
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWrite(SERVO_PIN, duty);
#else
  ledcWrite(0, duty);
#endif
}

int seedingMap[4][6] = {
  {1, 1, 0, 0, 1, 1},
  {0, 1, 0, 1, 1, 1},
  {1, 1, 0, 1, 1, 1},
  {1, 1, 1, 0, 1, 1}
};

const int X_STEP = 26;
const int X_DIR  = 27;
const int Y_STEP = 14;
const int Y_DIR  = 13;

const int LEFT_LIMIT_PIN  = 25;
const int RIGHT_LIMIT_PIN = 21;
const int MODE_SWITCH_PIN = 22;

int currentAngle = 0;
const int STEP_ANGLE = 60; // 6 лунок

const int START_BTN_PIN = 32;
const int ESTOP_BTN_PIN = 33;

const int STEPS_40MM = 3200;
const int STEPS_30MM = 2400;

void setup() {
  Serial.begin(115200);

  pinMode(X_STEP, OUTPUT); pinMode(X_DIR, OUTPUT);
  pinMode(Y_STEP, OUTPUT); pinMode(Y_DIR, OUTPUT);

  pinMode(LEFT_LIMIT_PIN, INPUT_PULLUP);
  pinMode(RIGHT_LIMIT_PIN, INPUT_PULLUP);
  pinMode(MODE_SWITCH_PIN, INPUT_PULLUP);
  pinMode(START_BTN_PIN, INPUT_PULLUP);
  pinMode(ESTOP_BTN_PIN, INPUT_PULLUP);

  servoAttach();
  servoWrite(0);

  Serial.println("Система готова. Один сервопривод (диск).");
}

void moveMotor(int stepPin, int dirPin, int steps, bool forward) {
  digitalWrite(dirPin, forward ? HIGH : LOW);
  for (int i = 0; i < steps; i++) {
    if (digitalRead(ESTOP_BTN_PIN) == LOW) return;
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(600);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(600);
  }
}

void primeDisc() {
  Serial.println("Прайминг...");
  for (int angle = 0; angle <= 180; angle += STEP_ANGLE) { servoWrite(angle); delay(200); }
  for (int angle = 180; angle >= 0; angle -= STEP_ANGLE) { servoWrite(angle); delay(200); }
  currentAngle = 0;
  servoWrite(currentAngle);
}

void processCell() {
  currentAngle += STEP_ANGLE;
  if (currentAngle > 180) currentAngle = 0;

  servoWrite(currentAngle);
  delay(500); // Ждем падения шарика

  Serial.print("[Шарик упал] ");
}

void driveRow(int row, bool moveRight, bool doSeed) {
  for (int i = 0; i < 6; i++) {
    int col = moveRight ? i : (5 - i);
    if (doSeed && seedingMap[row][col] == 1) {
      Serial.print("Посев. ");
      processCell();
    }
    if (i < 5) moveMotor(X_STEP, X_DIR, STEPS_40MM, moveRight);
  }

  Serial.println("Ждем концевик...");
  if (moveRight) { while (digitalRead(RIGHT_LIMIT_PIN) == HIGH) { delay(10); } }
  else           { while (digitalRead(LEFT_LIMIT_PIN)  == HIGH) { delay(10); } }
}

void loop() {
  if (digitalRead(ESTOP_BTN_PIN) == LOW) {
    Serial.println("E-STOP!");
    while (true) { delay(1000); }
  }

  if (digitalRead(START_BTN_PIN) == LOW) {
    delay(500);

    bool switchState = digitalRead(MODE_SWITCH_PIN);
    bool isSnakeMode = (switchState == HIGH);

    if (isSnakeMode) {
      Serial.println(">>> РЕЖИМ: ЗМЕЙКА <<<");
      primeDisc();
      bool moveRight = true;
      for (int row = 0; row < 4; row++) {
        driveRow(row, moveRight, true);
        if (row < 3) {
          Serial.println("Конвейер (NEMA 17): вниз на 3 см...");
          moveMotor(Y_STEP, Y_DIR, STEPS_30MM, true);
          moveRight = !moveRight;
        }
      }
    } else {
      Serial.println(">>> РЕЖИМ: ЗИГ-ЗАГ <<<");
      primeDisc();
      for (int row = 0; row < 4; row++) {
        driveRow(row, true, true);
        driveRow(row, false, false);
        if (row < 3) {
          Serial.println("Конвейер (NEMA 17): вниз на 3 см...");
          moveMotor(Y_STEP, Y_DIR, STEPS_30MM, true);
        }
      }
    }
    Serial.println("КАССЕТА ГОТОВА!");
    delay(3000);
  }
}
