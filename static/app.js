
import {
  FilesetResolver,
  HandLandmarker
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21/vision_bundle.mjs";

// -------------------- ELEMENTS --------------------

const $ = (id) => document.getElementById(id);

const video = $("webcam");
const canvas = $("landmark-canvas");
const ctx = canvas?.getContext("2d");
const cameraButton = $("camera-toggle");

// -------------------- CAMERA STATE --------------------

let landmarker = null;
let stream = null;
let raf = null;
let lastVideoTime = -1;

let history = [];
let lastGesture = null;
let efficiencyValues = [];

// IMPORTANT: This variable was missing in your original code.
let handWasVisible = false;

let cameraStarting = false;

// -------------------- NAVIGATION --------------------

const links = document.querySelectorAll(".nav-item");

links.forEach((link) => {
  link.addEventListener("click", () => {
    links.forEach((item) => item.classList.remove("active"));
    link.classList.add("active");
  });
});

const sections = [
  "overview",
  "vision",
  "analytics",
  "alerts",
  "machine"
].map((id) => $(id));

if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        links.forEach((link) => {
          link.classList.toggle(
            "active",
            link.getAttribute("href") === "#" + entry.target.id
          );
        });
      }
    });
  }, { rootMargin: "-25% 0px -60% 0px" });

  sections.forEach((section) => {
    if (section) observer.observe(section);
  });
}

// -------------------- GESTURE RECOGNITION --------------------

function fingerCount(points) {
  return [8, 12, 16, 20].filter((tip, i) =>
    points[tip].y < points[[6, 10, 14, 18][i]].y
  ).length;
}

function gestureName(n) {
  return ({
    1: "PRODUCTION",
    2: "INSPECTION",
    3: "MAINTENANCE",
    4: "PAUSE"
  })[n] || "UNKNOWN";
}

const connections = [
  [0,1],[1,2],[2,3],[3,4],
  [0,5],[5,6],[6,7],[7,8],
  [5,9],[9,10],[10,11],[11,12],
  [9,13],[13,14],[14,15],[15,16],
  [13,17],[17,18],[18,19],[19,20],
  [0,17]
];

// -------------------- DRAW HAND LANDMARKS --------------------

function draw(points) {
  if (!canvas || !ctx || !video) return;

  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!points) return;

  ctx.strokeStyle = "#54e0cc";
  ctx.lineWidth = 3;

  connections.forEach(([a, b]) => {
    ctx.beginPath();
    ctx.moveTo(
      points[a].x * canvas.width,
      points[a].y * canvas.height
    );
    ctx.lineTo(
      points[b].x * canvas.width,
      points[b].y * canvas.height
    );
    ctx.stroke();
  });

  points.forEach((p) => {
    ctx.beginPath();
    ctx.arc(
      p.x * canvas.width,
      p.y * canvas.height,
      4,
      0,
      Math.PI * 2
    );
    ctx.fillStyle = "#f4ffff";
    ctx.fill();
  });
}

// -------------------- SERVER COMMUNICATION --------------------

async function postGesture(gesture, count) {
  try {
    await fetch("/api/gesture", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        gesture,
        finger_count: count
      })
    });
  } catch (error) {
    console.error("Gesture update failed:", error);
  }
}

function postRelease() {
  fetch("/api/gesture/release", {
    method: "POST"
  }).catch((error) => {
    console.error("Release request failed:", error);
  });
}

// -------------------- CAMERA DETECTION LOOP --------------------

function loop() {
  if (!landmarker || !stream) return;

  try {
    if (
      video.readyState >= 2 &&
      video.currentTime !== lastVideoTime
    ) {
      lastVideoTime = video.currentTime;

      const result = landmarker.detectForVideo(
        video,
        performance.now()
      );

      const points = result.landmarks?.[0];

      if (points) {
        handWasVisible = true;

        draw(points);

        const count = fingerCount(points);
        const candidate = gestureName(count);

        $("finger-label").textContent = "Fingers: " + count;
        $("gesture-result").textContent = "Gesture: " + candidate;

        if (candidate !== "UNKNOWN") {
          history.push(candidate);

          if (history.length > 5) {
            history.shift();
          }

          if (
            history.length === 5 &&
            history.filter((x) => x === candidate).length >= 4 &&
            candidate !== lastGesture
          ) {
            lastGesture = candidate;
            postGesture(candidate, count);
          }
        } else {
          history = [];
        }

      } else {
        draw(null);

        history = [];
        lastGesture = null;

        $("finger-label").textContent = "Fingers: 0";
        $("gesture-result").textContent = "Gesture: NO HAND";

        if (handWasVisible) {
          postRelease();
          handWasVisible = false;
        }
      }
    }

    raf = requestAnimationFrame(loop);

  } catch (error) {
    console.error("Hand detection error:", error);
    stopCamera("Hand detection failed: " + error.message);
  }
}

// -------------------- START CAMERA --------------------

async function startCamera() {
  if (cameraStarting || stream) return;

  cameraStarting = true;
  cameraButton.disabled = true;

  $("camera-help").textContent =
    "Loading hand recognition model...";

  $("camera-status").textContent = "CONNECTING";

  try {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error(
        "Camera access requires HTTPS or localhost."
      );
    }

    if (!video || !canvas || !ctx) {
      throw new Error(
        "Camera video or landmark canvas element is missing."
      );
    }

    // Load MediaPipe
    const vision = await FilesetResolver.forVisionTasks(
      "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21/wasm"
    );

    landmarker = await HandLandmarker.createFromOptions(
      vision,
      {
        baseOptions: {
          modelAssetPath:
            "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
          delegate: "CPU"
        },
        runningMode: "VIDEO",
        numHands: 1,
        minHandDetectionConfidence: 0.65,
        minHandPresenceConfidence: 0.65,
        minTrackingConfidence: 0.6
      }
    );

    // Request webcam access
    stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: "user",
        width: { ideal: 640 },
        height: { ideal: 480 }
      },
      audio: false
    });

    video.srcObject = stream;

    await video.play();

    lastVideoTime = -1;
    handWasVisible = false;
    history = [];
    lastGesture = null;

    cameraButton.textContent = "Stop camera";

    $("camera-status").textContent = "CONNECTED";

    $("camera-help").textContent =
      "Camera active. Video is processed locally in this browser.";

    loop();

  } catch (error) {
    console.error("Camera startup error:", error);

    $("camera-help").textContent =
      "Camera error: " + error.message;

    $("camera-status").textContent = "NOT CONNECTED";

    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
    }

    stream = null;

    if (video) {
      video.srcObject = null;
    }

    if (landmarker) {
      landmarker.close();
    }

    landmarker = null;

    cameraButton.textContent = "Start camera";

  } finally {
    cameraStarting = false;
    cameraButton.disabled = false;
  }
}

// -------------------- STOP CAMERA --------------------

function stopCamera(errorMessage = null) {
  if (raf !== null) {
    cancelAnimationFrame(raf);
    raf = null;
  }

  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
  }

  stream = null;

  if (landmarker) {
    landmarker.close();
  }

  landmarker = null;

  if (video) {
    video.pause();
    video.srcObject = null;
  }

  draw(null);

  history = [];
  lastGesture = null;
  handWasVisible = false;
  lastVideoTime = -1;

  cameraButton.textContent = "Start camera";

  $("camera-status").textContent = errorMessage
    ? "ERROR"
    : "NOT STARTED";

  $("gesture-result").textContent = "Gesture: NO HAND";
  $("finger-label").textContent = "Fingers: 0";

  $("camera-help").textContent =
    errorMessage || "Camera stopped.";

  postRelease();
}

// -------------------- CAMERA BUTTON --------------------

cameraButton.addEventListener("click", () => {
  if (cameraStarting) return;

  if (stream) {
    stopCamera();
  } else {
    startCamera();
  }
});

// -------------------- CHART FUNCTIONS --------------------

function canvasSetup(id) {
  const el = $(id);

  if (!el) return null;

  const w = el.clientWidth || 400;
  const h = Number(el.getAttribute("height")) || 120;
  const d = window.devicePixelRatio || 1;

  el.width = w * d;
  el.height = h * d;

  const c = el.getContext("2d");
  c.setTransform(d, 0, 0, d, 0, 0);

  return { c, w, h };
}

function lineChart(id, values, color, suffix = "") {
  const setup = canvasSetup(id);
  if (!setup) return;

  const { c, w, h } = setup;

  const l = 10;
  const r = w - 10;
  const t = 12;
  const b = h - 20;

  c.clearRect(0, 0, w, h);
  c.strokeStyle = "#263750";

  for (let i = 0; i < 4; i++) {
    const y = t + i * (b - t) / 3;

    c.beginPath();
    c.moveTo(l, y);
    c.lineTo(r, y);
    c.stroke();
  }

  if (!values.length) return;

  const min = Math.min(0, ...values);
  const max = Math.max(10, ...values);
  const range = Math.max(1, max - min);

  const pts = values.map((v, i) => ({
    x: l + i * (r - l) / Math.max(1, values.length - 1),
    y: b - (v - min) / range * (b - t)
  }));

  c.beginPath();

  pts.forEach((p, i) => {
    if (i) c.lineTo(p.x, p.y);
    else c.moveTo(p.x, p.y);
  });

  c.strokeStyle = color;
  c.lineWidth = 2.5;
  c.stroke();

  c.fillStyle = "#8294ad";
  c.font = "9px sans-serif";

  c.fillText(
    values.at(-1) + suffix,
    Math.max(10, r - 40),
    10
  );
}

function barChart(items) {
  const setup = canvasSetup("production-chart");
  if (!setup) return;

  const { c, w, h } = setup;

  c.clearRect(0, 0, w, h);

  if (!items.length) {
    c.fillStyle = "#8294ad";
    c.font = "10px sans-serif";
    c.fillText("No gesture activity recorded yet.", 10, 30);
    return;
  }

  const data = items.slice(-8);
  const max = Math.max(1, ...data.map((x) => x.total));

  const gap = 9;
  const bw = (w - 20 - gap * (data.length - 1)) / data.length;

  data.forEach((x, i) => {
    const bh = x.total / max * (h - 32);
    const bx = 10 + i * (bw + gap);
    const by = h - 21 - bh;

    c.fillStyle = "#58d7cd";
    c.fillRect(bx, by, bw, bh);

    c.fillStyle = "#8294ad";
    c.font = "8px sans-serif";
    c.textAlign = "center";
    c.fillText(x.hour, bx + bw / 2, h - 5);
  });

  c.textAlign = "left";
}

// -------------------- ACTIVITY --------------------

function showActivity(items) {
  $("activity-list").innerHTML = items.length
    ? items.map((x) =>
        '<div class="activity-item">' +
        '<span class="activity-time">' +
        x.created_at.slice(11, 19) +
        '</span>' +
        '<span class="activity-message"><b>' +
        x.gesture +
        '</b><small>' +
        x.username +
        ' · ' +
        x.machine_status +
        '</small></span></div>'
      ).join("")
    : '<div class="empty-state">No gesture activity recorded yet.</div>';
}

function showAlerts(items) {
  $("alert-list").innerHTML = items.length
    ? items.map((x) =>
        '<div class="alert-row ' + x.severity + '">' +
        '<span class="alert-mark">' +
        (x.severity === "danger" ? "!" : "△") +
        '</span><div><b>' +
        x.message +
        '</b><small>' +
        x.time +
        ' · Demo notification</small></div></div>'
      ).join("")
    : '<div class="empty-state">✓ No active demo alerts.</div>';
}

// -------------------- DASHBOARD REFRESH --------------------

async function refresh() {
  try {
    const response = await fetch("/api/status", {
      cache: "no-store"
    });

    if (response.status === 401) {
      location.href = "/login";
      return;
    }

    if (!response.ok) {
      throw new Error("Dashboard status request failed.");
    }

    const d = await response.json();

    $("clock").textContent = d.clock;
    $("machine-status").textContent = d.machine_status;
    $("mode-label").textContent = "Mode: " + d.mode;

    $("production-events").textContent = d.production_events;
    $("efficiency").textContent = d.efficiency;
    $("chart-current").textContent = d.efficiency + "%";

    $("efficiency-bar").style.width = d.efficiency + "%";

    $("gesture-label").textContent = "Gesture: " + d.gesture;

    $("temperature").textContent = Number(d.temperature).toFixed(1);
    $("pressure").textContent = Number(d.pressure).toFixed(2);
    $("vibration").textContent = Number(d.vibration).toFixed(2);

    $("temperature-bar").style.width =
      Math.min(100, d.temperature / 90 * 100) + "%";

    $("pressure-bar").style.width =
      Math.min(100, d.pressure / 10 * 100) + "%";

    $("vibration-bar").style.width =
      Math.min(100, d.vibration / 6 * 100) + "%";

    const color =
      d.machine_status === "RUNNING" ? "#45d6a0" :
      d.machine_status === "PAUSED" ? "#f1b95d" :
      "#ff777f";

    $("machine-status").style.color = color;
    $("status-dot").style.background = color;
    $("machine-model-status").textContent = d.machine_status;

    $("machine-model").classList.toggle(
      "running",
      d.machine_status === "RUNNING"
    );

    $("machine-model").classList.toggle(
      "paused",
      d.machine_status === "PAUSED"
    );

    showActivity(d.activity || []);
    showAlerts(d.alerts || []);

    const analyticsResponse = await fetch("/api/analytics");

    if (!analyticsResponse.ok) {
      throw new Error("Analytics request failed.");
    }

    const a = await analyticsResponse.json();

    const samples = a.sensors || [];

    lineChart(
      "efficiency-chart",
      samples.map((x) => x.efficiency),
      "#58d7cd",
      "%"
    );

    barChart(a.production_by_hour || []);

  } catch (error) {
    console.error("Dashboard refresh error:", error);
  }
}

// -------------------- CLEAR ALERTS --------------------

$("clear-alerts").addEventListener("click", async () => {
  try {
    await fetch("/api/clear-alerts", {
      method: "POST"
    });

    showAlerts([]);
  } catch (error) {
    console.error("Could not clear alerts:", error);
  }
});

// -------------------- INITIALIZE --------------------

refresh();

setInterval(refresh, 2000);

window.addEventListener("resize", () => refresh());

window.addEventListener("beforeunload", () => {
  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
  }

  if (landmarker) {
    landmarker.close();
  }
});
