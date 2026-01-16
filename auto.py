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
# YOLO SETUP
# =============================
model = YOLO("yolov8n.pt")

cap = cv2.VideoCapture(1)

cv2.namedWindow("Turret Vision", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Turret Vision", 1280, 720)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# =============================
# TARGET STATE
# =============================
selected_target_idx = 0
active_target_ids = []

had_active_target = False  # <-- STATE TRACKING

# =============================
# CROSSHAIR SMOOTHING
# =============================
smoothed_cx, smoothed_cy = None, None
smoothing_factor = 0.3

# =============================
# MAIN LOOP
# =============================
while cap.isOpened():
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

    has_active_target = False  # reset each frame

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

                cx = (x1 + x2) // 2
                cy = y1 + int(0.35 * (y2 - y1))

                if smoothed_cx is None:
                    smoothed_cx, smoothed_cy = cx, cy
                else:
                    smoothed_cx = int(smoothed_cx * (1 - smoothing_factor) + cx * smoothing_factor)
                    smoothed_cy = int(smoothed_cy * (1 - smoothing_factor) + cy * smoothing_factor)

                cv2.circle(frame, (smoothed_cx, smoothed_cy), 5, (0, 0, 255), -1)

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
    # DISPLAY
    # =============================
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
