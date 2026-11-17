from flask import Flask, render_template, Response, jsonify
import cv2
import mediapipe as mp
import threading
import time
from collections import deque
from datetime import datetime

app = Flask(__name__)

# This is a local software demonstration. It does not control real machinery.
state = {
    "machine_status": "STOPPED",
    "mode": "IDLE",
    "gesture": "NO HAND",
    "finger_count": 0,
    "production_events": 0,
    "efficiency": 85,
    "camera_ok": False,
    "activity": []
}

state_lock = threading.Lock()
frame_lock = threading.Lock()
latest_jpeg = None
camera_started = False


def add_activity(message):
    stamp = datetime.now().strftime("%H:%M:%S")
    with state_lock:
        state["activity"].insert(0, {"time": stamp, "message": message})
        state["activity"] = state["activity"][:10]


def count_fingers(hand_landmarks):
    points = hand_landmarks.landmark
    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]
    return sum(1 for tip, pip in zip(tips, pips) if points[tip].y < points[pip].y)


def gesture_for(count):
    return {
        1: "PRODUCTION",
        2: "INSPECTION",
        3: "MAINTENANCE",
        4: "PAUSE"
    }.get(count, "UNKNOWN")


def apply_gesture(gesture):
    with state_lock:
        if gesture == "PRODUCTION":
            state["machine_status"] = "RUNNING"
            state["mode"] = "PRODUCTION"
            state["production_events"] += 1
        elif gesture == "INSPECTION":
            state["machine_status"] = "RUNNING"
            state["mode"] = "INSPECTION"
        elif gesture == "MAINTENANCE":
            state["machine_status"] = "STOPPED"
            state["mode"] = "MAINTENANCE"
        elif gesture == "PAUSE":
            state["machine_status"] = "PAUSED"
            state["mode"] = "PAUSE"
    add_activity("Mode changed to " + gesture.title())


def camera_worker():
    global latest_jpeg, camera_started

    mp_hands = mp.solutions.hands
    drawing = mp.solutions.drawing_utils
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        with state_lock:
            state["camera_ok"] = False
            state["gesture"] = "CAMERA NOT FOUND"
        add_activity("Webcam could not be opened")
        camera_started = True
        return

    with state_lock:
        state["camera_ok"] = True
    add_activity("Webcam connected")

    history = deque(maxlen=5)
    last_gesture = None
    last_efficiency_tick = time.time()

    try:
        with mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        ) as hands:
            while True:
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.05)
                    continue

                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb)

                current_gesture = "NO HAND"
                current_count = 0

                if results.multi_hand_landmarks:
                    hand = results.multi_hand_landmarks[0]
                    drawing.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)
                    current_count = count_fingers(hand)
                    detected = gesture_for(current_count)

                    if detected != "UNKNOWN":
                        history.append(detected)
                    else:
                        history.clear()

                    if len(history) == history.maxlen:
                        stable = max(set(history), key=history.count)
                        if history.count(stable) >= 4:
                            current_gesture = stable
                            if stable != last_gesture:
                                apply_gesture(stable)
                                last_gesture = stable
                    else:
                        current_gesture = "DETECTING"
                else:
                    history.clear()
                    last_gesture = None

                with state_lock:
                    state["gesture"] = current_gesture
                    state["finger_count"] = current_count

                now = time.time()
                if now - last_efficiency_tick >= 4:
                    with state_lock:
                        if state["mode"] == "PRODUCTION":
                            state["efficiency"] = min(99, state["efficiency"] + 1)
                        elif state["mode"] in ("PAUSE", "MAINTENANCE"):
                            state["efficiency"] = max(60, state["efficiency"] - 1)
                    last_efficiency_tick = now

                # Small on-frame label for clarity
                cv2.putText(frame, f"Gesture: {current_gesture}", (18, 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (40, 230, 190), 2)
                cv2.putText(frame, f"Fingers: {current_count}", (18, 68),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

                encoded, buffer = cv2.imencode(
                    ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80]
                )
                if encoded:
                    with frame_lock:
                        latest_jpeg = buffer.tobytes()
                camera_started = True
    finally:
        cap.release()


def mjpeg_stream():
    while True:
        with frame_lock:
            frame = latest_jpeg
        if frame is not None:
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        time.sleep(0.04)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    return Response(mjpeg_stream(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/status")
def api_status():
    with state_lock:
        snapshot = dict(state)
        snapshot["activity"] = list(state["activity"])
    snapshot["clock"] = datetime.now().strftime("%d %b %Y  •  %H:%M:%S")
    return jsonify(snapshot)


if __name__ == "__main__":
    add_activity("Dashboard service started")
    worker = threading.Thread(target=camera_worker, daemon=True)
    worker.start()
    print("\nSmart Manufacturing Dashboard")
    print("Open http://127.0.0.1:5000 in your browser")
    print("Press Ctrl+C in this terminal to stop.\n")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
