FORGEIQ - SMART MANUFACTURING WEBSITE
=====================================

WHAT THIS PROJECT DOES
- Runs your existing MediaPipe hand recognition in Python.
- Streams the webcam feed to a local Flask website.
- Shows machine status, gesture, finger count, production event count,
  simulated efficiency, an efficiency trend chart, and activity log.

IMPORTANT
This is a classroom/demo software simulation only. The efficiency is simulated
and "production events" count gesture activations, not actual manufactured
products. It does not control or connect to physical industrial machinery.

SETUP ON WINDOWS / VS CODE
1. Extract this ZIP file.
2. In VS Code, choose File > Open Folder and open the extracted
   smart_manufacturing_website folder.
3. Open Terminal > New Terminal.
4. (Recommended) Create a virtual environment:
      py -3.11 -m venv .venv
      .venv\Scripts\activate
5. Install dependencies:
      python -m pip install --upgrade pip
      pip install -r requirements.txt
6. Start the website:
      python app.py
7. Open this address in Chrome or Edge:
      http://127.0.0.1:5000

HOW TO USE
- Allow camera access if the browser asks.
- Keep your palm facing the webcam.
- Hold one, two, three, or four fingers steadily for a moment.
- Press Ctrl+C in the VS Code terminal to stop the server.

GESTURES
1 finger: Production
2 fingers: Inspection
3 fingers: Maintenance
4 fingers: Pause

TROUBLESHOOTING
- If the camera cannot open, close other apps using the webcam and try again.
- If the browser feed is blank, check the VS Code terminal for an error.
- If mediapipe installation fails, use Python 3.11 (64-bit) and reinstall
  from requirements.txt.
- If port 5000 is busy, close the other Flask app or change port=5000
  near the bottom of app.py to another port such as 5001.
