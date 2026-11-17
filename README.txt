FORGEIQ PRO - COMPLETE CLASSROOM PROJECT
========================================
FEATURES
- Local Flask website and demo operator login
- MediaPipe/OpenCV hand recognition and webcam feed
- 1 finger Production, 2 Inspection, 3 Maintenance, 4 Pause
- SQLite storage for gesture events and sensor history
- Simulated temperature, pressure, vibration and efficiency
- Illustrative smart alerts / maintenance warnings
- Efficiency and production charts
- CSV export of gesture events
- CSS 3D-style machine visualization

DEMO LOGIN
Username: operator
Password: forgeiq123

IMPORTANT
This is a classroom software simulation only. Sensor readings, alerts, and
efficiency are simulated, not real measurements. Production events count
gesture activations, not actual manufactured items. The 3D machine is an
illustration. This application does not control physical machinery and is
not an industrial safety system. The demo login is not production-grade
authentication. Do not expose this development server to the public internet.

WINDOWS / VS CODE
1. Extract the ZIP and open the ForgeIQ_Pro folder in VS Code.
2. Open Terminal > New Terminal.
3. Recommended: Python 3.11 (64-bit).
4. Create and activate a virtual environment:
   py -3.11 -m venv .venv
   .venv\Scripts\activate
5. Install dependencies:
   python -m pip install --upgrade pip
   pip install -r requirements.txt
6. Start:
   python app.py
7. Open http://127.0.0.1:5000 in Chrome or Edge.
8. Sign in with the demo login above and allow webcam access.

Press Ctrl+C in the terminal to stop.
Database is created automatically in instance/forgeiq.db.
