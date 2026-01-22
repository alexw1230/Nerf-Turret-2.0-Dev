from ultralytics import YOLO
import cv2
import serial
import time
import sys

# =============================
# SERIAL CONFIG
# =============================
SERIAL_PORT = "COM3"
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
CENTER_Y = FRAME_H // 2
SECOND_MONITOR_X = 1920
SECOND_MONITOR_Y = 0

timeout = 3.0
last_target_time = time.time()

# PAN CONFIG (UNCHANGED)
PAN_LIMIT = 50.0
MAX_PAN_SPEED = 270.0
PAN_ACCEL = 2000.0

# TILT CONFIG (PAN-LIKE)
TILT_LIMIT = 20.0
MAX_TILT_SPEED = 180.0
TILT_ACCEL = 1500.0

SERVO_SEND_INTERVAL = 0.02
last_servo_send = 0

# =============================
# YOLO
# =============================
model = YOLO("yolov8n.pt")

cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

cv2.namedWindow("Turret Vision", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Turret Vision", 1280, 720)
cv2.moveWindow("Turret Vision", 1920, 0)
cv2.setWindowProperty(
    "Turret Vision",
    cv2.WND_PROP_FULLSCREEN,
    cv2.WINDOW_FULLSCREEN
)
# =============================
# STATE
# =============================
selected_target_idx = 0
active_target_ids = []
had_active_target = False

pan_angle = 0.0
tilt_angle = 0.0
pan_vel = 0.0
tilt_vel = 0.0

last_time = time.time()

# =============================
# SMOOTHING
# =============================
smoothing_factor = 0.7
smoothed_cx = None
smoothed_cy = None

# =============================
# HELPERS
# =============================
def send_servo_command(pan, tilt):
    x = int(round(pan + 90))
    y = int(round(tilt + 90))
    ser.write(f"{x},{y}\n".encode())

def response_curve(x, expo=1.6):
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

        if selected_target_idx >= len(ids):
            selected_target_idx = 0

        selected_id = ids[selected_target_idx]

        for box, tid in zip(boxes, ids):
            x1, y1, x2, y2 = map(int, box)

            if tid == selected_id:
                has_active_target = True
                last_target_time = now  # ✅ FIX

                cx = (x1 + x2) // 2
                target_y = y1 + int(0.33 * (y2 - y1))  # 2/3 up box

                smoothed_cx = cx if smoothed_cx is None else int(
                    smoothed_cx * (1 - smoothing_factor) + cx * smoothing_factor
                )
                smoothed_cy = target_y if smoothed_cy is None else int(
                    smoothed_cy * (1 - smoothing_factor) + target_y * smoothing_factor
                )

                cv2.circle(frame, (smoothed_cx, smoothed_cy), 5, (0,0,255), -1)

                # ===== PAN =====
                err_x = response_curve((smoothed_cx - CENTER_X) / FRAME_W)
                desired_pan_vel = err_x * MAX_PAN_SPEED

                dv = desired_pan_vel - pan_vel
                pan_vel += max(-PAN_ACCEL*dt, min(PAN_ACCEL*dt, dv))
                pan_angle += pan_vel * dt
                pan_angle = max(-PAN_LIMIT, min(PAN_LIMIT, pan_angle))

                # ===== TILT (PAN-STYLE) =====
                err_y = response_curve((CENTER_Y - smoothed_cy) / FRAME_H)
                desired_tilt_vel = err_y * MAX_TILT_SPEED

                dv = desired_tilt_vel - tilt_vel
                tilt_vel += max(-TILT_ACCEL*dt, min(TILT_ACCEL*dt, dv))
                tilt_angle += tilt_vel * dt
                tilt_angle = max(-TILT_LIMIT, min(TILT_LIMIT, tilt_angle))

                color = (0,0,255)
                thickness = 3
            else:
                color = (0,255,0)
                thickness = 2

            cv2.rectangle(frame, (x1,y1), (x2,y2), color, thickness)

    # =============================
    # SIGNALING (2 / 3)
    # =============================
    if has_active_target and not had_active_target:
        ser.write(b"3\n")
        print("TRACK ACQUIRED -> 3")

    elif not has_active_target and had_active_target:
        ser.write(b"2\n")
        print("TRACK LOST -> 2")

    had_active_target = has_active_target

    # =============================
    # TIMEOUT RETURN TO ZERO
    # =============================
    if not has_active_target and now - last_target_time > timeout:
        pan_angle = tilt_angle = pan_vel = tilt_vel = 0.0
        send_servo_command(0,0)

    # =============================
    # SEND SERVO
    # =============================
    if now - last_servo_send >= SERVO_SEND_INTERVAL:
        send_servo_command(pan_angle, tilt_angle)
        last_servo_send = now

    # =============================
    # DISPLAY
    # =============================
    cv2.circle(frame, (CENTER_X, CENTER_Y), 5, (255,0,0), 2)
    cv2.putText(frame, f"Pan {pan_angle:+.1f}", (20,40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
    cv2.putText(frame, f"Tilt {tilt_angle:+.1f}", (20,80),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

    cv2.imshow("Turret Vision", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# =============================
# CLEANUP (RETURN TO ZERO)
# =============================
send_servo_command(0,0)
ser.close()
cap.release()
cv2.destroyAllWindows()
sys.exit(0)
