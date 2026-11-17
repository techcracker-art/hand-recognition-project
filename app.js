const $ = (id) => document.getElementById(id);
const historyValues = [];
let lastActivityKey = "";

function drawChart(value) {
  const canvas = $("efficiency-chart");
  const ctx = canvas.getContext("2d");
  const width = canvas.clientWidth || 500;
  const height = 145;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  ctx.scale(ratio, ratio);
  ctx.clearRect(0, 0, width, height);

  const left = 8, right = width - 8, top = 12, bottom = 118;
  ctx.strokeStyle = "#263750";
  ctx.lineWidth = 1;
  for (let i = 0; i < 4; i++) {
    const y = top + i * ((bottom - top) / 3);
    ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(right, y); ctx.stroke();
  }

  historyValues.push(Number(value));
  if (historyValues.length > 18) historyValues.shift();
  while (historyValues.length < 18) historyValues.unshift(historyValues[0] || Number(value));

  const points = historyValues.map((v, i) => ({
    x: left + i * ((right - left) / 17),
    y: bottom - (Math.max(0, Math.min(100, v)) / 100) * (bottom - top)
  }));

  const gradient = ctx.createLinearGradient(0, top, 0, bottom);
  gradient.addColorStop(0, "rgba(80,214,208,.28)");
  gradient.addColorStop(1, "rgba(80,214,208,0)");
  ctx.beginPath();
  ctx.moveTo(points[0].x, bottom);
  points.forEach(p => ctx.lineTo(p.x, p.y));
  ctx.lineTo(points[points.length - 1].x, bottom);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  ctx.beginPath();
  points.forEach((p, i) => i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y));
  ctx.strokeStyle = "#58d7cd";
  ctx.lineWidth = 2.5;
  ctx.stroke();
  const last = points[points.length - 1];
  ctx.beginPath(); ctx.arc(last.x, last.y, 4, 0, Math.PI * 2);
  ctx.fillStyle = "#8af0df"; ctx.fill();
}

function renderActivity(items) {
  const target = $("activity-list");
  if (!items || !items.length) {
    target.innerHTML = '<div class="empty-state">Waiting for system events…</div>';
    return;
  }
  target.innerHTML = items.map(item =>
    `<div class="activity-item"><span class="activity-time">${item.time}</span><span class="activity-message">${item.message}</span></div>`
  ).join("");
}

async function refresh() {
  try {
    const response = await fetch("/api/status", {cache: "no-store"});
    const data = await response.json();

    $("clock").textContent = data.clock;
    $("machine-status").textContent = data.machine_status;
    $("mode-label").textContent = "Mode: " + data.mode;
    $("production-events").textContent = data.production_events;
    $("efficiency").textContent = data.efficiency;
    $("chart-current").textContent = data.efficiency + "%";
    $("efficiency-bar").style.width = data.efficiency + "%";
    $("gesture-label").textContent = "Gesture: " + data.gesture;
    $("finger-label").textContent = "Fingers detected: " + data.finger_count;
    $("camera-status").textContent = data.camera_ok ? "CONNECTED" : "CHECK CAMERA";

    const status = $("machine-status");
    status.style.color = data.machine_status === "RUNNING" ? "#45d6a0" :
      data.machine_status === "PAUSED" ? "#f1b95d" : "#ff777f";
    $("status-dot").style.background = data.machine_status === "RUNNING" ? "#45d6a0" :
      data.machine_status === "PAUSED" ? "#f1b95d" : "#ff777f";

    renderActivity(data.activity);
    drawChart(data.efficiency);
  } catch (error) {
    $("camera-status").textContent = "SERVER OFFLINE";
  }
}
refresh();
setInterval(refresh, 1000);
window.addEventListener("resize", () => {
  const value = Number($("efficiency").textContent) || 85;
  drawChart(value);
});
