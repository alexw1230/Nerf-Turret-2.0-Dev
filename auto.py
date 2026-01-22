from ultralytics import YOLO
import cv2
import serial
import time

# =============================
# SERIAL CONFIG
# =============================
SERIAL_PORT = "COM3"   # CHANGE THIS
BAUD_RATE = 115200

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
time.sleep(2)
print("Serial connected")

# =============================
# CAMERA / SERVO CONFIG
# =============================
FRAME_W = 640
FRAME_H = 480
CENTER_X = FRAME_W // 2

PAN_LIMIT = 50.0
MAX_PAN_SPEED = 270.0  # deg/sec
PAN_ACCEL = 2000.0     # deg/sec^2, very snappy

SERVO_SEND_INTERVAL = 0.02  # 50Hz
last_servo_send = 0

# =============================
# YOLO SETUP
# =============================
model = YOLO("yolov8n.pt")

cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

cv2.namedWindow("Turret Vision", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Turret Vision", 1280, 720)

# =============================
# TARGET STATE
# =============================
selected_target_idx = 0
active_target_ids = []
had_active_target = False

# =============================
# SERVO STATE
# =============================
pan_angle = 0.0
tilt_angle = 0.0  # locked at 0
pan_vel_current = 0.0
last_time = time.time()

# =============================
# CROSSHAIR SMOOTHING
# =============================
smoothing_factor = 0.3  # more responsive
# BEFORE MAIN LOOP
smoothed_cx = None
smoothed_cy = None

# Warm-up frames to initialize tracker
for _ in range(3):
    ret, frame = cap.read()
    if ret:
        _ = model.track(frame, persist=True, classes=[0], conf=0.4, imgsz=416, verbose=False)
smoothing_factor = 0.7
# =============================
# HELPERS
# =============================
def send_servo_command(pan, tilt):
    x = int(round(pan + 90))
    y = int(round(tilt + 90))
    ser.write(f"{x},{y}\n".encode("utf-8"))

def response_curve(x, expo=1.3):
    return x ** expo if x >= 0 else -((-x) ** expo)

# =============================
# MAIN LOOP
# =============================
while cap.isOpened():
    now = time.time()
    dt = now - last_time
    last_time = now

    ret, frame = cap.read()
    if not ret:
        break

    results = model.track(
        frame,
        persist=True,
        classes=[0],
        conf=0.4,
        imgsz=416,
        verbose=False
    )

    has_active_target = False

    if results[0].boxes is not None and results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy
        ids = results[0].boxes.id.cpu().tolist()
        active_target_ids = ids

        if selected_target_idx >= len(active_target_ids):
            selected_target_idx = 0

        selected_id = active_target_ids[selected_target_idx] if active_target_ids else None

        for box, track_id in zip(boxes, ids):
            x1, y1, x2, y2 = map(int, box)

            if track_id == selected_id:
                has_active_target = True
                color = (0, 0, 255)
                thickness = 3

                # =============================
                # SMOOTHING
                # =============================
                cx = (x1 + x2) // 2

                if smoothed_cx is None:
                    smoothed_cx = cx
                else:
                    smoothed_cx = int(smoothed_cx * (1 - smoothing_factor) + cx * smoothing_factor)

                cv2.circle(frame, (smoothed_cx, (y1 + y2)//2), 5, (0, 0, 255), -1)

                # =============================
                # DESIRED VELOCITY
                # =============================
                err_x = smoothed_cx - CENTER_X
                err_x = response_curve(err_x / FRAME_W)
                desired_vel = err_x * MAX_PAN_SPEED

                # =============================
                # ACCELERATION / DECELERATION
                # =============================
                vel_diff = desired_vel - pan_vel_current
                max_change = PAN_ACCEL * dt
                if abs(vel_diff) > max_change:
                    vel_diff = max_change if vel_diff > 0 else -max_change
                pan_vel_current += vel_diff

                pan_angle += pan_vel_current * dt
                pan_angle = max(-PAN_LIMIT, min(PAN_LIMIT, pan_angle))

                # tilt locked
                tilt_angle = 0.0

            else:
                color = (0, 255, 0)
                thickness = 2

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

    # =============================
    # SERIAL STATE TRANSITIONS
    # =============================
    if has_active_target and not had_active_target:
        ser.write(b"3\n")
        print("TRACK ACQUIRED -> sent 3")
    elif not has_active_target and had_active_target:
        ser.write(b"2\n")
        print("TRACK LOST -> sent 2")

    had_active_target = has_active_target

    # =============================
    # SEND SERVO (throttled)
    # =============================
    if now - last_servo_send >= SERVO_SEND_INTERVAL:
        send_servo_command(pan_angle, tilt_angle)
        last_servo_send = now

    # =============================
    # DISPLAY
    # =============================
    cv2.circle(frame, (CENTER_X, FRAME_H//2), 5, (255, 0, 0), 2)
    cv2.putText(frame, f"Pan: {pan_angle:+.1f}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
    cv2.putText(frame, f"Tilt: {tilt_angle:+.1f}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
    cv2.imshow("Turret Vision", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord("n") and len(active_target_ids) > 1:
        selected_target_idx = (selected_target_idx + 1) % len(active_target_ids)
    elif key == ord("q"):
        break

# =============================
# CLEANUP
# =============================
ser.close()
cap.release()
cv2.destroyAllWindows()
