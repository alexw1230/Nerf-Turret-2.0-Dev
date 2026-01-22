import pygame
import cv2
import time
import serial

# =============================
# CONFIG
# =============================
PAN_LIMIT = 75.0
TILT_LIMIT = 20.0
DEADZONE = 0.1

SPEED_SLOW = 45.0
SPEED_MED  = 90.0
SPEED_FAST = 180.0

CAMERA_INDEX = 1

SERIAL_PORT = "COM3"
BAUD_RATE = 115200

# Xbox mappings (Windows)
BTN_A = 0
AXIS_RT = 5
TRIGGER_THRESHOLD = 0.5
HAT_INDEX = 0

# =============================
# SERIAL SEND FUNCTIONS
# =============================
def send_servo_command(ser, pan, tilt):
    x = int(round(pan + 90))
    y = int(round(tilt + 90))
    ser.write(f"{x},{y}\n".encode("utf-8"))

def send_relay_command(ser, state):
    ser.write(f"{state}\n".encode("utf-8"))

# =============================
# HELPERS
# =============================
def apply_curve(x, expo=2):
    return x ** expo if x >= 0 else -((-x) ** expo)

# =============================
# INIT PYGAME
# =============================
pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    raise RuntimeError("No controller detected")

joystick = pygame.joystick.Joystick(0)
joystick.init()

print(f"Controller connected: {joystick.get_name()}")

# =============================
# INIT SERIAL
# =============================
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
time.sleep(2)
print("Serial connected")

# =============================
# INIT CAMERA
# =============================
cap = cv2.VideoCapture(CAMERA_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

cv2.namedWindow("Turret Manual Control", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Turret Manual Control", 1280, 720)

# =============================
# STATE
# =============================
pan_angle = 0.0
tilt_angle = 0.0

speed_mode = "FAST"
MAX_SPEED = SPEED_FAST

last_time = time.time()
prev_a = False
firing = False
prev_hat = (0, 0)

# =============================
# MAIN LOOP
# =============================
while True:
    now = time.time()
    dt = now - last_time
    last_time = now

    pygame.event.pump()

    # =============================
    # D-PAD SPEED CONTROL
    # =============================
    hat = joystick.get_hat(HAT_INDEX)

    if hat != prev_hat:
        if hat[1] == 1:
            speed_mode = "FAST"
            MAX_SPEED = SPEED_FAST
        elif hat[1] == -1:
            speed_mode = "SLOW"
            MAX_SPEED = SPEED_SLOW
        elif hat[0] == 1 or hat[0] == -1:
            speed_mode = "MED"
            MAX_SPEED = SPEED_MED

    prev_hat = hat

    # =============================
    # STICKS
    # =============================
    stick_x = joystick.get_axis(0)
    stick_y = joystick.get_axis(1)

    if abs(stick_x) < DEADZONE:
        stick_x = 0.0
    if abs(stick_y) < DEADZONE:
        stick_y = 0.0

    stick_y = -stick_y

    stick_x = apply_curve(stick_x)
    stick_y = apply_curve(stick_y)

    pan_angle  += stick_x * MAX_SPEED * dt
    tilt_angle += stick_y * MAX_SPEED * dt

    pan_angle  = max(-PAN_LIMIT,  min(PAN_LIMIT,  pan_angle))
    tilt_angle = max(-TILT_LIMIT, min(TILT_LIMIT, tilt_angle))

    # =============================
    # RECENTER
    # =============================
    a_pressed = joystick.get_button(BTN_A)
    if a_pressed and not prev_a:
        pan_angle = 0.0
        tilt_angle = 0.0
        send_servo_command(ser, pan_angle, tilt_angle)
        print("Recentered")

    prev_a = a_pressed

    # =============================
    # TRIGGER FIRE
    # =============================
    rt = joystick.get_axis(AXIS_RT)
    if rt < 0:
        rt = (rt + 1) / 2

    if rt > TRIGGER_THRESHOLD and not firing:
        firing = True
        send_relay_command(ser, 1)
        print("FIRE")

    elif rt <= TRIGGER_THRESHOLD and firing:
        firing = False
        send_relay_command(ser, 0)
        print("FIRE STOP")

    # =============================
    # SEND SERVO DATA
    # =============================
    send_servo_command(ser, pan_angle, tilt_angle)

    # =============================
    # CAMERA
    # =============================
    ret, frame = cap.read()
    if not ret:
        print("Camera read failed")
        break

    cv2.putText(frame, f"Pan: {pan_angle:+.1f}",
                (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(frame, f"Tilt: {tilt_angle:+.1f}",
                (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(frame, f"Speed: {speed_mode} ({int(MAX_SPEED)} deg/s)",
                (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    h, w = frame.shape[:2]
    cv2.circle(frame, (w // 2, h // 2), 5, (0, 0, 255), -1)

    cv2.imshow("Turret Manual Control", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# =============================
# CLEANUP
# =============================
ser.close()
cap.release()
cv2.destroyAllWindows()
pygame.quit()
