import os, io, csv, time, random, sqlite3, threading
from datetime import datetime
from collections import deque
import cv2, mediapipe as mp
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response, make_response, flash
from werkzeug.security import generate_password_hash, check_password_hash

BASE=os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(BASE,"instance"),exist_ok=True)
DB=os.path.join(BASE,"instance","forgeiq.db")
app=Flask(__name__)
app.secret_key=os.environ.get("FORGEIQ_SECRET","demo-secret-change-before-deployment")
lock=threading.RLock()
frame_lock=threading.Lock()
latest_frame=None
gesture_history=deque(maxlen=5)
last_gesture=None
active_operator="system"
state={"machine_status":"STOPPED","mode":"IDLE","gesture":"NO HAND","finger_count":0,
       "production_events":0,"efficiency":85,"temperature":42.0,"pressure":5.2,
       "vibration":1.4,"camera_ok":False,"alerts":[]}

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
    with db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT, display_name TEXT, role TEXT)")
        c.execute("""CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, created_at TEXT, username TEXT,
                  gesture TEXT, mode TEXT, machine_status TEXT, event_type TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS sensor_history(id INTEGER PRIMARY KEY, created_at TEXT,
                  temperature REAL, pressure REAL, vibration REAL, efficiency INTEGER)""")
        if not c.execute("SELECT id FROM users WHERE username='operator'").fetchone():
            c.execute("INSERT INTO users(username,password_hash,display_name,role) VALUES(?,?,?,?)",
                      ("operator",generate_password_hash("forgeiq123"),"Demo Operator","Production Operator"))
        c.commit()

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def inner(*a,**kw):
        if "username" not in session: return redirect(url_for("login"))
        return fn(*a,**kw)
    return inner

def record_event(gesture,mode,status):
    with db() as c:
        c.execute("INSERT INTO events(created_at,username,gesture,mode,machine_status,event_type) VALUES(?,?,?,?,?,?)",
                  (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),active_operator,
                   gesture,mode,status,"GESTURE"))
        c.commit()

def alert(msg,severity="warning"):
    with lock:
        if not any(x["message"]==msg for x in state["alerts"]):
            state["alerts"].insert(0,{"message":msg,"severity":severity,"time":datetime.now().strftime("%H:%M:%S")})
            state["alerts"]=state["alerts"][:8]

@app.route("/login",methods=["GET","POST"])
def login():
    global active_operator
    if request.method=="POST":
        u=request.form.get("username","").strip(); p=request.form.get("password","")
        with db() as c: user=c.execute("SELECT * FROM users WHERE username=?",(u,)).fetchone()
        if user and check_password_hash(user["password_hash"],p):
            session.clear(); session.update(username=user["username"],display_name=user["display_name"],role=user["role"])
            active_operator=user["username"]
            return redirect(url_for("index"))
        flash("Incorrect username or password.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("login"))

def finger_count(hand):
    lm=hand.landmark
    return sum(lm[t].y < lm[p].y for t,p in zip([8,12,16,20],[6,10,14,18]))

def gesture_name(n):
    return {1:"PRODUCTION",2:"INSPECTION",3:"MAINTENANCE",4:"PAUSE"}.get(n,"UNKNOWN")

def apply_gesture(g):
    global last_gesture
    with lock:
        if g=="PRODUCTION":
            state["machine_status"]="RUNNING"; state["mode"]="PRODUCTION"; state["production_events"]+=1
        elif g=="INSPECTION":
            state["machine_status"]="RUNNING"; state["mode"]="INSPECTION"
        elif g=="MAINTENANCE":
            state["machine_status"]="STOPPED"; state["mode"]="MAINTENANCE"
        elif g=="PAUSE":
            state["machine_status"]="PAUSED"; state["mode"]="PAUSE"
        mode=state["mode"]; status=state["machine_status"]
    record_event(g,mode,status); last_gesture=g

def camera_worker():
    global latest_frame,last_gesture
    mp_hands=mp.solutions.hands; draw=mp.solutions.drawing_utils
    cam=cv2.VideoCapture(0)
    if not cam.isOpened():
        with lock: state["camera_ok"]=False; state["gesture"]="CAMERA NOT FOUND"
        alert("Webcam unavailable. Close other camera apps and restart.","warning"); return
    with lock: state["camera_ok"]=True
    try:
        with mp_hands.Hands(static_image_mode=False,max_num_hands=1,min_detection_confidence=.7,min_tracking_confidence=.7) as hands:
            while True:
                ok,frame=cam.read()
                if not ok: time.sleep(.05); continue
                frame=cv2.flip(frame,1); rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB); result=hands.process(rgb)
                g="NO HAND"; count=0
                if result.multi_hand_landmarks:
                    hand=result.multi_hand_landmarks[0]; draw.draw_landmarks(frame,hand,mp_hands.HAND_CONNECTIONS)
                    count=finger_count(hand); candidate=gesture_name(count)
                    if candidate!="UNKNOWN": gesture_history.append(candidate)
                    else: gesture_history.clear()
                    if len(gesture_history)==5:
                        stable=max(set(gesture_history),key=gesture_history.count)
                        if gesture_history.count(stable)>=4:
                            g=stable
                            if stable!=last_gesture: apply_gesture(stable)
                        else: g="DETECTING"
                    else: g="DETECTING"
                else:
                    gesture_history.clear(); last_gesture=None
                with lock: state["gesture"]=g; state["finger_count"]=count
                cv2.putText(frame,f"Gesture: {g}",(16,32),cv2.FONT_HERSHEY_SIMPLEX,.7,(50,225,190),2)
                cv2.putText(frame,f"Fingers: {count}",(16,63),cv2.FONT_HERSHEY_SIMPLEX,.6,(255,255,255),2)
                ok,buf=cv2.imencode(".jpg",frame,[int(cv2.IMWRITE_JPEG_QUALITY),78])
                if ok:
                    with frame_lock: latest_frame=buf.tobytes()
    finally: cam.release()

def sensor_worker():
    while True:
        time.sleep(3)
        with lock:
            state["temperature"]=round(max(35,min(92,state["temperature"]+random.uniform(-1.2,1.4))),1)
            state["pressure"]=round(max(3,min(9.5,state["pressure"]+random.uniform(-.18,.18))),2)
            state["vibration"]=round(max(.3,min(6.5,state["vibration"]+random.uniform(-.22,.25))),2)
            if state["mode"]=="PRODUCTION": state["efficiency"]=min(99,state["efficiency"]+random.choice([0,0,1]))
            elif state["mode"] in ("PAUSE","MAINTENANCE"): state["efficiency"]=max(55,state["efficiency"]-random.choice([0,0,1]))
            t,p,v,e=state["temperature"],state["pressure"],state["vibration"],state["efficiency"]
        # Illustrative demo thresholds only; not safety limits.
        if t>=75: alert(f"Demo temperature elevated: {t} °C","danger")
        if p>=8: alert(f"Demo pressure elevated: {p} bar","warning")
        if v>=4: alert(f"Demo vibration elevated: {v} mm/s. Maintenance review suggested.","warning")
        with db() as c:
            c.execute("INSERT INTO sensor_history(created_at,temperature,pressure,vibration,efficiency) VALUES(?,?,?,?,?)",
                      (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),t,p,v,e)); c.commit()

def video_stream():
    while True:
        with frame_lock: frame=latest_frame
        if frame: yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"+frame+b"\r\n"
        time.sleep(.04)

@app.route("/")
@login_required
def index(): return render_template("index.html",display_name=session.get("display_name"),role=session.get("role"))

@app.route("/video_feed")
@login_required
def video_feed(): return Response(video_stream(),mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/status")
@login_required
def api_status():
    with lock: d=dict(state); d["alerts"]=list(state["alerts"])
    with db() as c:
        d["activity"]=[dict(x) for x in c.execute("SELECT * FROM events ORDER BY id DESC LIMIT 8")]
        d["event_total"]=c.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    d["clock"]=datetime.now().strftime("%d %b %Y • %H:%M:%S")
    return jsonify(d)

@app.route("/api/analytics")
@login_required
def analytics():
    with db() as c:
        sensors=[dict(x) for x in c.execute("SELECT * FROM (SELECT * FROM sensor_history ORDER BY id DESC LIMIT 24) ORDER BY id")]
        hours=[dict(x) for x in c.execute("""SELECT substr(created_at,12,2) hour,COUNT(*) total FROM events
                 WHERE date(created_at)=date('now','localtime') GROUP BY hour ORDER BY hour""")]
    return jsonify({"sensors":sensors,"production_by_hour":[{"hour":x["hour"]+":00","total":x["total"]} for x in hours]})

@app.route("/reports/production.csv")
@login_required
def export_csv():
    out=io.StringIO(); w=csv.writer(out)
    w.writerow(["Timestamp","Operator","Gesture","Mode","Machine Status","Event Type"])
    with db() as c:
        for row in c.execute("SELECT created_at,username,gesture,mode,machine_status,event_type FROM events ORDER BY id DESC"): w.writerow(list(row))
    res=make_response("\\ufeff"+out.getvalue())
    res.headers["Content-Type"]="text/csv; charset=utf-8"
    res.headers["Content-Disposition"]="attachment; filename=forgeiq_production_report.csv"
    return res

@app.route("/api/clear-alerts",methods=["POST"])
@login_required
def clear_alerts():
    with lock: state["alerts"]=[]
    return jsonify({"ok":True})

init_db()
if __name__=="__main__":
    threading.Thread(target=camera_worker,daemon=True).start()
    threading.Thread(target=sensor_worker,daemon=True).start()
    print("\\nForgeIQ Pro: http://127.0.0.1:5000\\nDemo login: operator / forgeiq123\\n")
    app.run(host="127.0.0.1",port=5000,debug=False,threaded=True)
