import csv
import hmac
import io
import os
import random
import threading
import time
from datetime import datetime
from functools import wraps

from flask import Flask, Response, flash, jsonify, make_response, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "local-development-only-change-this")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
)

DEMO_USERNAME = os.environ.get("FORGEIQ_USERNAME", "operator")
DEMO_PASSWORD = os.environ.get("FORGEIQ_PASSWORD", "forgeiq123")

lock = threading.RLock()
state = {
    "machine_status": "STOPPED",
    "mode": "IDLE",
    "gesture": "NO HAND",
    "finger_count": 0,
    "production_events": 0,
    "efficiency": 85,
    "temperature": 42.0,
    "pressure": 5.2,
    "vibration": 1.4,
    "alerts": [],
    "activity": [],
    "sensor_history": [],
    "last_sensor_update": 0.0,
}


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def add_activity(message, gesture="SYSTEM"):
    state["activity"].insert(0, {
        "created_at": now_text(),
        "gesture": gesture,
        "message": message,
        "username": session.get("username", "system"),
        "machine_status": state["machine_status"],
        "mode": state["mode"],
    })
    del state["activity"][20:]


def add_alert(message, severity="warning"):
    if not any(item["message"] == message for item in state["alerts"]):
        state["alerts"].insert(0, {
            "message": message,
            "severity": severity,
            "time": datetime.now().strftime("%H:%M:%S"),
        })
        del state["alerts"][8:]


def update_simulated_sensors():
    """Generate demo readings; these are not real industrial sensor measurements."""
    current = time.time()
    if current - state["last_sensor_update"] < 4:
        return

    state["temperature"] = round(max(35.0, min(92.0, state["temperature"] + random.uniform(-1.2, 1.4))), 1)
    state["pressure"] = round(max(3.0, min(9.5, state["pressure"] + random.uniform(-0.18, 0.18))), 2)
    state["vibration"] = round(max(0.3, min(6.5, state["vibration"] + random.uniform(-0.22, 0.25))), 2)

    if state["mode"] == "PRODUCTION":
        state["efficiency"] = min(99, state["efficiency"] + random.choice([0, 0, 1]))
    elif state["mode"] in ("PAUSE", "MAINTENANCE"):
        state["efficiency"] = max(55, state["efficiency"] - random.choice([0, 0, 1]))

    state["last_sensor_update"] = current
    state["sensor_history"].append({
        "created_at": now_text(),
        "temperature": state["temperature"],
        "pressure": state["pressure"],
        "vibration": state["vibration"],
        "efficiency": state["efficiency"],
    })
    del state["sensor_history"][:-24]

    # Illustrative classroom thresholds only; not engineering or safety limits.
    if state["temperature"] >= 75:
        add_alert("Demo temperature elevated: " + str(state["temperature"]) + " °C", "danger")
    if state["pressure"] >= 8:
        add_alert("Demo pressure elevated: " + str(state["pressure"]) + " bar", "warning")
    if state["vibration"] >= 4:
        add_alert("Demo vibration elevated: " + str(state["vibration"]) + " mm/s. Review suggested.", "warning")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "username" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Please sign in again."}), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.get("/healthz")
def health():
    return jsonify({"status": "ok", "service": "ForgeIQ"})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        valid_user = hmac.compare_digest(username, DEMO_USERNAME)
        valid_password = hmac.compare_digest(password, DEMO_PASSWORD)
        if valid_user and valid_password:
            session.clear()
            session["username"] = username
            with lock:
                add_activity("Operator signed in")
            return redirect(url_for("index"))
        flash("Incorrect username or password.")
    return render_template("login.html")


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/")
@login_required
def index():
    return render_template("index.html", display_name=session.get("username", "Operator"))


@app.post("/api/gesture")
@login_required
def receive_gesture():
    payload = request.get_json(silent=True) or {}
    gesture = str(payload.get("gesture", "")).upper()
    try:
        fingers = int(payload.get("finger_count", 0))
    except (TypeError, ValueError):
        fingers = 0

    modes = {
        "PRODUCTION": ("RUNNING", "PRODUCTION"),
        "INSPECTION": ("RUNNING", "INSPECTION"),
        "MAINTENANCE": ("STOPPED", "MAINTENANCE"),
        "PAUSE": ("PAUSED", "PAUSE"),
    }
    if gesture not in modes:
        return jsonify({"error": "Unrecognised gesture command."}), 400

    with lock:
        state["machine_status"], state["mode"] = modes[gesture]
        state["gesture"] = gesture
        state["finger_count"] = max(0, min(4, fingers))
        if gesture == "PRODUCTION":
            state["production_events"] += 1
        add_activity("Gesture command: " + gesture.title(), gesture)
        return jsonify({
            "ok": True,
            "machine_status": state["machine_status"],
            "mode": state["mode"],
            "production_events": state["production_events"],
        })


@app.post("/api/gesture/release")
@login_required
def release_gesture():
    with lock:
        state["gesture"] = "NO HAND"
        state["finger_count"] = 0
    return jsonify({"ok": True})


@app.get("/api/status")
@login_required
def api_status():
    with lock:
        update_simulated_sensors()
        result = {key: value for key, value in state.items() if key != "last_sensor_update"}
        result["alerts"] = list(state["alerts"])
        result["activity"] = list(state["activity"][:8])
    result["clock"] = datetime.now().strftime("%d %b %Y • %H:%M:%S")
    result["operator"] = session.get("username", "Operator")
    return jsonify(result)


@app.get("/api/analytics")
@login_required
def analytics():
    with lock:
        samples = list(state["sensor_history"])
        activities = list(state["activity"])
    hourly = {}
    for item in activities:
        if item.get("gesture") in ("PRODUCTION", "INSPECTION", "MAINTENANCE", "PAUSE"):
            hour = item["created_at"][11:13] + ":00"
            hourly[hour] = hourly.get(hour, 0) + 1
    return jsonify({
        "sensors": samples,
        "production_by_hour": [{"hour": key, "total": hourly[key]} for key in sorted(hourly)],
    })


@app.post("/api/clear-alerts")
@login_required
def clear_alerts():
    with lock:
        state["alerts"] = []
    return jsonify({"ok": True})


@app.get("/reports/production.csv")
@login_required
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp", "Operator", "Gesture", "Mode", "Machine Status"])
    with lock:
        rows = list(state["activity"])
    for item in rows:
        writer.writerow([
            item["created_at"], item["username"], item["gesture"],
            item["mode"], item["machine_status"],
        ])
    response = make_response("\ufeff" + output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=forgeiq_activity_report.csv"
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
