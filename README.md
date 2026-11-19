# ForgeIQ – Cloud-ready demonstration

ForgeIQ is a browser-based smart-manufacturing dashboard demonstration.

## Features
- Flask website and demo operator login
- Browser camera access (camera permission is requested by the visitor)
- MediaPipe hand tracking in the visitor's browser
- Gesture commands: 1 finger Production, 2 Inspection, 3 Maintenance, 4 Pause
- Simulated temperature, pressure, vibration and efficiency
- Demo alerts, activity charts and CSV export
- CSS machine illustration

## Run locally
Use Python 3.11 or later in a virtual environment.

\`\`\`bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
\`\`\`

Set these environment variables for local testing:
- SECRET_KEY: a long random secret
- FORGEIQ_USERNAME: demo login username
- FORGEIQ_PASSWORD: demo login password
- COOKIE_SECURE=false when testing on localhost

Run:
\`\`\`bash
python app.py
\`\`\`
Open http://127.0.0.1:5000.

## Deploy on Render
- Create a Render Web Service from this GitHub repository.
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app --workers 1 --threads 4 --timeout 120`
- Add environment variables: SECRET_KEY, FORGEIQ_USERNAME, FORGEIQ_PASSWORD, COOKIE_SECURE=true.
- Use a generated secret; do not commit credentials to GitHub.

## Important limitations
This is a classroom software demonstration, not an industrial control system.
Temperature, pressure, vibration and efficiency are simulated, and production
events count gesture activations rather than physical products. The machine
illustration is CSS-based. The webcam video and gesture inference run in the
visitor's browser; only recognised gesture commands are sent to Flask.

The demo uses in-memory activity and sensor history. On a free cloud instance,
those values can reset when the process restarts or sleeps. Add a persistent
database before using it for long-term recordkeeping.

The provided demo login is basic demonstration authentication. Do not expose
sensitive information or use it as a production account system. This application
does not control physical equipment and is not a safety-rated control.
