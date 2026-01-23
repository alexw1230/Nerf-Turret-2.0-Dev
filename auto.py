#Computer Vision + Automatic Tracking


from ultralytics import YOLO
import cv2
import serial
import time
import sys

#Config and open serial
SERIAL_PORT = "COM3"
BAUD_RATE = 115200
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
time.sleep(2)
print("Serial connected")

#Display settings
FRAME_W = 640
FRAME_H = 480
CENTER_X = FRAME_W // 2
CENTER_Y = FRAME_H // 2
SECOND_MONITOR_X = 1920
SECOND_MONITOR_Y = 0

#Time init
timeout = 3.0
last_target_time = time.time()


#Pan Tilt params
PAN_LIMIT = 50.0
MAX_PAN_SPEED = 270.0
PAN_ACCEL = 2000.0

TILT_LIMIT = 20.0
MAX_TILT_SPEED = 180.0
TILT_ACCEL = 2000.0

SERVO_SEND_INTERVAL = 0.02
last_servo_send = 0

#Model load
model = YOLO("yolov8n.pt")

#Cam init
cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

#Display window init
cv2.namedWindow("Turret Vision", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Turret Vision", 1280, 720)
cv2.moveWindow("Turret Vision", 1920, 0)
cv2.setWindowProperty(
    "Turret Vision",
    cv2.WND_PROP_FULLSCREEN,
    cv2.WINDOW_FULLSCREEN
)

#Target tracking
selected_target_idx = 0
active_target_ids = []
had_active_target = False

#State vars
pan_angle = 0.0
tilt_angle = 0.0
pan_vel = 0.0
tilt_vel = 0.0

last_time = time.time()

#Smoothing factor to reduce jittering
smoothing_factor = 0.7
smoothed_cx = None
smoothed_cy = None

#Serial sender helper
def send_servo_command(pan, tilt):
    x = int(round(pan + 90))
    y = int(round(tilt + 90))
    ser.write(f"{x},{y}\n".encode())

#Nonlinear curve for smoother tracking, faster sense at edges
def response_curve(x, expo=1.35):
    return x ** expo if x >= 0 else -((-x) ** expo)

#Main
while cap.isOpened():
    now = time.time()
    dt = now - last_time
    last_time = now

    ret, frame = cap.read()
    if not ret:
        break
    
    #Yolo reads people
    results = model.track(
        frame,
        persist=True,
        classes=[0],
        conf=0.4,
        imgsz=416,
        verbose=False
    )

    has_active_target = False

    #Detection processing
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
                last_target_time = now

                #Aim point is middle x of box and 2/3 up of box
                cx = (x1 + x2) // 2
                target_y = y1 + int(0.33 * (y2 - y1))

                #Expo smoothing
                smoothed_cx = cx if smoothed_cx is None else int(
                    smoothed_cx * (1 - smoothing_factor) + cx * smoothing_factor
                )
                smoothed_cy = target_y if smoothed_cy is None else int(
                    smoothed_cy * (1 - smoothing_factor) + target_y * smoothing_factor
                )

                #Draw aim point
                cv2.circle(frame, (smoothed_cx, smoothed_cy), 5, (0,0,255), -1)

                #Pan ctrl
                err_x = response_curve((smoothed_cx - CENTER_X) / FRAME_W)
                desired_pan_vel = err_x * MAX_PAN_SPEED

                dv = desired_pan_vel - pan_vel
                pan_vel += max(-PAN_ACCEL*dt, min(PAN_ACCEL*dt, dv))
                pan_angle += pan_vel * dt
                pan_angle = max(-PAN_LIMIT, min(PAN_LIMIT, pan_angle))
                
                #Tilt ctrl
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

            #Draw targeting box
            cv2.rectangle(frame, (x1,y1), (x2,y2), color, thickness)

    #On target acq or loss of acq
    if has_active_target and not had_active_target: #Acquired
        ser.write(b"3\n") #Changes indicator on app

    elif not has_active_target and had_active_target: #Lost
        ser.write(b"2\n") #Changes indicator on app

    had_active_target = has_active_target

    #Reset to 0,0 on timeout
    if not has_active_target and now - last_target_time > timeout:
        pan_angle = tilt_angle = pan_vel = tilt_vel = 0.0
        send_servo_command(0,0)

    #Safety for oversend rate
    if now - last_servo_send >= SERVO_SEND_INTERVAL:
        send_servo_command(pan_angle, tilt_angle)
        last_servo_send = now
    
    #Overlay
    cv2.circle(frame, (CENTER_X, CENTER_Y), 5, (255,0,0), 2)
    cv2.putText(frame, f"Pan {pan_angle:+.1f}", (20,40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
    cv2.putText(frame, f"Tilt {tilt_angle:+.1f}", (20,80),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

    cv2.imshow("Turret Vision", frame)

    #Quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

#Reset on cleanup
send_servo_command(0,0)
ser.close()
cap.release()
cv2.destroyAllWindows()
sys.exit(0)
