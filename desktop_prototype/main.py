
import cv2
import mediapipe as mp
import time
from collections import deque
from datetime import datetime

# ==========================================
# 1. MEDIAPIPE INITIALIZATION
# ==========================================

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# ==========================================
# 2. SYSTEM VARIABLES
# ==========================================

machine_status = "STOPPED"
operating_mode = "IDLE"

detected_gesture = "NONE"
finger_count = 0

production_count = 0
efficiency = 85

history = deque(maxlen=5)
activity_log = deque(maxlen=7)

last_gesture = None
last_efficiency_update = time.time()

# ==========================================
# 3. FINGER COUNTING
# ==========================================

def count_fingers(hand_landmarks):

    landmarks = hand_landmarks.landmark

    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]

    count = 0

    for tip, pip in zip(tips, pips):

        if landmarks[tip].y < landmarks[pip].y:
            count += 1

    return count


# ==========================================
# 4. GESTURE RECOGNITION
# ==========================================

def recognize_gesture(count):

    gestures = {
        1: "PRODUCTION",
        2: "INSPECTION",
        3: "MAINTENANCE",
        4: "PAUSE"
    }

    return gestures.get(count, "UNKNOWN")


# ==========================================
# 5. ACTIVITY LOG
# ==========================================

def add_log(message):

    current_time = datetime.now().strftime("%H:%M:%S")

    activity_log.appendleft(
        current_time + "  " + message
    )


# ==========================================
# 6. MACHINE CONTROL SIMULATION
# ==========================================

def update_machine(gesture):

    global machine_status
    global operating_mode
    global production_count

    if gesture == "PRODUCTION":

        machine_status = "RUNNING"
        operating_mode = "PRODUCTION"
        production_count += 1

    elif gesture == "INSPECTION":

        machine_status = "RUNNING"
        operating_mode = "INSPECTION"

    elif gesture == "MAINTENANCE":

        machine_status = "STOPPED"
        operating_mode = "MAINTENANCE"

    elif gesture == "PAUSE":

        machine_status = "PAUSED"
        operating_mode = "PAUSE"

    add_log("Mode changed: " + gesture)


# ==========================================
# 7. SIMULATED EFFICIENCY
# ==========================================

def update_efficiency():

    global efficiency
    global last_efficiency_update

    now = time.time()

    if now - last_efficiency_update >= 3:

        if operating_mode == "PRODUCTION":
            efficiency = min(99, efficiency + 1)

        elif operating_mode == "INSPECTION":
            efficiency = max(70, efficiency - 1)

        elif operating_mode in ["MAINTENANCE", "PAUSE"]:
            efficiency = max(60, efficiency - 1)

        last_efficiency_update = now


# ==========================================
# 8. DASHBOARD DESIGN
# ==========================================

def create_dashboard(frame):

    global efficiency

    dashboard = cv2.copyMakeBorder(
        frame,
        90, 30, 0, 430,
        cv2.BORDER_CONSTANT,
        value=(20, 25, 35)
    )

    # HEADER

    cv2.putText(
        dashboard,
        "AI SMART MANUFACTURING SYSTEM",
        (20, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (0, 255, 255),
        2
    )

    current_date = datetime.now().strftime(
        "%d-%m-%Y"
    )

    current_time = datetime.now().strftime(
        "%H:%M:%S"
    )

    cv2.putText(
        dashboard,
        current_date + "  " + current_time,
        (680, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1
    )

    # PANEL TITLE

    cv2.putText(
        dashboard,
        "INDUSTRIAL CONTROL PANEL",
        (670, 115),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 255, 255),
        2
    )

    # MACHINE STATUS

    status_color = (0, 255, 0)

    if machine_status == "PAUSED":
        status_color = (0, 165, 255)

    elif machine_status == "STOPPED":
        status_color = (0, 0, 255)

    cv2.putText(
        dashboard,
        "Machine: " + machine_status,
        (670, 165),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        status_color,
        2
    )

    # OPERATING MODE

    cv2.putText(
        dashboard,
        "Mode: " + operating_mode,
        (670, 210),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 0),
        2
    )

    # GESTURE

    cv2.putText(
        dashboard,
        "Gesture: " + detected_gesture,
        (670, 255),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )

    cv2.putText(
        dashboard,
        "Finger Count: " + str(finger_count),
        (670, 295),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (200, 200, 200),
        1
    )

    # PRODUCTION EVENTS

    cv2.putText(
        dashboard,
        "Production Events: " + str(production_count),
        (670, 345),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 200, 255),
        2
    )

    # EFFICIENCY

    cv2.putText(
        dashboard,
        "Machine Efficiency (SIMULATED)",
        (670, 390),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (255, 255, 255),
        1
    )

    cv2.putText(
        dashboard,
        str(efficiency) + "%",
        (670, 425),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.85,
        (0, 255, 0),
        2
    )

    # EFFICIENCY BAR

    cv2.rectangle(
        dashboard,
        (670, 445),
        (970, 465),
        (80, 80, 80),
        2
    )

    bar_width = int(296 * efficiency / 100)

    cv2.rectangle(
        dashboard,
        (672, 447),
        (672 + bar_width, 463),
        (0, 200, 0),
        -1
    )

    # COMMAND GUIDE

    cv2.putText(
        dashboard,
        "GESTURE COMMANDS",
        (670, 495),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        (0, 255, 255),
        1
    )

    commands = [
        "1 Finger - PRODUCTION",
        "2 Fingers - INSPECTION",
        "3 Fingers - MAINTENANCE",
        "4 Fingers - PAUSE"
    ]

    for i, command in enumerate(commands):

        cv2.putText(
            dashboard,
            command,
            (670, 520 + i * 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (230, 230, 230),
            1
        )

    # ACTIVITY LOG

    cv2.putText(
        dashboard,
        "RECENT ACTIVITY",
        (20, 535),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 255, 255),
        1
    )

    for i, log in enumerate(activity_log):

        cv2.putText(
            dashboard,
            log,
            (20, 560 + i * 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (255, 255, 255),
            1
        )

    cv2.putText(
        dashboard,
        "Press Q to EXIT",
        (670, 635),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (180, 180, 180),
        1
    )

    return dashboard


# ==========================================
# 9. START WEBCAM
# ==========================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():

    print("ERROR: Webcam not detected.")

    hands.close()
    raise SystemExit

print("-----------------------------------")
print("AI SMART MANUFACTURING SYSTEM")
print("Dashboard Started Successfully")
print("-----------------------------------")
print("Show your hand to the webcam.")
print("Press Q to exit.")

add_log("System started")


# ==========================================
# 10. MAIN PROGRAM
# ==========================================

try:

    while True:

        success, frame = cap.read()

        if not success:

            print("Camera frame unavailable.")
            break

        frame = cv2.flip(frame, 1)

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        results = hands.process(rgb)

        detected_gesture = "DETECTING"

        if results.multi_hand_landmarks:

            for hand_landmarks in results.multi_hand_landmarks:

                mp_draw.draw_landmarks(
                    frame,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS
                )

                finger_count = count_fingers(
                    hand_landmarks
                )

                gesture = recognize_gesture(
                    finger_count
                )

                cv2.putText(
                    frame,
                    "Fingers: " + str(finger_count),
                    (20, 55),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (0, 255, 0),
                    2
                )

                if gesture != "UNKNOWN":

                    history.append(gesture)

                else:

                    history.clear()

                if len(history) == history.maxlen:

                    stable_gesture = max(
                        set(history),
                        key=history.count
                    )

                    if history.count(stable_gesture) >= 4:

                        detected_gesture = stable_gesture

                        if stable_gesture != last_gesture:

                            update_machine(
                                stable_gesture
                            )

                            last_gesture = stable_gesture

        else:

            history.clear()
            last_gesture = None
            detected_gesture = "NO HAND"
            finger_count = 0

        update_efficiency()

        dashboard = create_dashboard(frame)

        cv2.imshow(
            "AI SMART MANUFACTURING DASHBOARD",
            dashboard
        )

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break


finally:

    cap.release()
    hands.close()
    cv2.destroyAllWindows()

    print("Dashboard closed.")
    print("Thank you for using the system.")
