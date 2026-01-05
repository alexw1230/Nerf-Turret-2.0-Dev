from ultralytics import YOLO
import cv2

# Load nano model
model = YOLO("yolov8n.pt")

# Open camera
cap = cv2.VideoCapture(1)

cv2.namedWindow("Turret Vision", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Turret Vision", 1280, 720)  # any size you want
selected_target_idx = 0
active_target_ids = []

# Optional performance tweaks
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Track people only
    results = model.track(
        frame,
        persist=True,
        classes=[0],      # person only
        conf=0.4,
        imgsz=640,
        verbose=False
    )

    if results[0].boxes is not None and results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy
        ids = results[0].boxes.id.cpu().tolist()

        # Update active targets list (unique + stable order)
        active_target_ids = ids

        # Clamp selected index if needed
        if selected_target_idx >= len(active_target_ids):
            selected_target_idx = 0

        selected_id = active_target_ids[selected_target_idx]

        for box, track_id in zip(boxes, ids):
            x1, y1, x2, y2 = map(int, box)

            if track_id == selected_id:
                color = (0, 0, 255)  # active target = red
                thickness = 3

                # Draw crosshair at center
                cx = (x1 + x2) // 2
                cy = y1 + int(0.4 * (y2 - y1))
                cv2.circle(frame, (cx, cy), radius=5, color=(0, 0, 255), thickness=-1)

            else:
                color = (0, 255, 0)  # other targets = green
                thickness = 2

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)



    cv2.imshow("Turret Vision", frame)
    key = cv2.waitKey(1) & 0xFF

    if key == ord("n") and len(active_target_ids) > 1:
        selected_target_idx = (selected_target_idx + 1) % len(active_target_ids)

    elif key == ord("q"):
        cap.release()
        cv2.destroyAllWindows()
        exit(0)


cap.release()
cv2.destroyAllWindows()
