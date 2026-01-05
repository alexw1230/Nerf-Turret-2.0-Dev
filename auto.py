from ultralytics import YOLO
import cv2

# Load YOLOv8 nano model
model = YOLO("yolov8n.pt")

# Open camera
cap = cv2.VideoCapture(1)

cv2.namedWindow("Turret Vision", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Turret Vision", 1280, 720)

# Optional performance tweaks
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Target selection
selected_target_idx = 0
active_target_ids = []

# Crosshair smoothing
smoothed_cx, smoothed_cy = None, None
smoothing_factor = 0.3  # 0 = no smoothing, 1 = full lag

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    results = model.track(
        frame,
        persist=True,
        classes=[0],  # person only
        conf=0.4,
        imgsz=416,    # smaller input for speed
        verbose=False
    )

    if results[0].boxes is not None and results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy
        ids = results[0].boxes.id.cpu().tolist()

        # Update active target list
        active_target_ids = ids

        # Clamp selected index
        if selected_target_idx >= len(active_target_ids):
            selected_target_idx = 0

        if len(active_target_ids) > 0:
            selected_id = active_target_ids[selected_target_idx]
        else:
            selected_id = None

        # Draw boxes and crosshair
        for box, track_id in zip(boxes, ids):
            x1, y1, x2, y2 = map(int, box)

            if track_id == selected_id:
                color = (0, 0, 255)  # RED for active target
                thickness = 3

                # Arm-safe crosshair: top 35% of box
                cx = (x1 + x2) // 2
                cy = y1 + int(0.35 * (y2 - y1))

                # Smooth the crosshair
                if smoothed_cx is None:
                    smoothed_cx, smoothed_cy = cx, cy
                else:
                    smoothed_cx = int(smoothed_cx * (1 - smoothing_factor) + cx * smoothing_factor)
                    smoothed_cy = int(smoothed_cy * (1 - smoothing_factor) + cy * smoothing_factor)

                cv2.circle(frame, (smoothed_cx, smoothed_cy), radius=5, color=(0, 0, 255), thickness=-1)

            else:
                color = (0, 255, 0)  # GREEN for other targets
                thickness = 2

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

    # Show frame
    cv2.imshow("Turret Vision", frame)

    # Key handling
    key = cv2.waitKey(1) & 0xFF
    if key == ord("n") and len(active_target_ids) > 1:
        selected_target_idx = (selected_target_idx + 1) % len(active_target_ids)
    elif key == ord("q"):
        cap.release()
        cv2.destroyAllWindows()
        exit(0)
