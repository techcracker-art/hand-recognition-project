import { FilesetResolver, HandLandmarker } from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21/vision_bundle.mjs";

const $ = (id) => document.getElementById(id);
const video = $("webcam");
const canvas = $("landmark-canvas");
const ctx = canvas.getContext("2d");
let landmarker = null, stream = null, raf = null, lastVideoTime = -1;
let history = [], lastGesture = null, efficiencyValues = [];

const links = document.querySelectorAll(".nav-item");
links.forEach((link) => link.addEventListener("click", () => {
  links.forEach((item) => item.classList.remove("active"));
  link.classList.add("active");
}));
const sections = ["overview", "vision", "analytics", "alerts", "machine"].map((id) => document.getElementById(id));
if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        links.forEach((link) => link.classList.toggle("active", link.getAttribute("href") === "#" + entry.target.id));
      }
    });
  }, {rootMargin: "-25% 0px -60% 0px"});
  sections.forEach((section) => section && observer.observe(section));
}

function fingerCount(points) {
  return [8, 12, 16, 20].filter((tip, i) => points[tip].y < points[[6, 10, 14, 18][i]].y).length;
}
function gestureName(n) {
  return ({1:"PRODUCTION", 2:"INSPECTION", 3:"MAINTENANCE", 4:"PAUSE"})[n] || "UNKNOWN";
}
const connections = [[0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],[5,9],[9,10],[10,11],[11,12],[9,13],[13,14],[14,15],[15,16],[13,17],[17,18],[18,19],[19,20],[0,17]];
function draw(points) {
  canvas.width = video.videoWidth; canvas.height = video.videoHeight;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!points) return;
  ctx.strokeStyle = "#54e0cc"; ctx.lineWidth = 3;
  connections.forEach(([a,b]) => {
    ctx.beginPath(); ctx.moveTo(points[a].x*canvas.width, points[a].y*canvas.height);
    ctx.lineTo(points[b].x*canvas.width, points[b].y*canvas.height); ctx.stroke();
  });
  points.forEach(p => {
    ctx.beginPath(); ctx.arc(p.x*canvas.width,p.y*canvas.height,4,0,Math.PI*2);
    ctx.fillStyle="#f4ffff"; ctx.fill();
  });
}
async function postGesture(gesture, count) {
  await fetch("/api/gesture", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({gesture,finger_count:count})});
}
async function postRelease() {
  fetch("/api/gesture/release", {method:"POST"}).catch(()=>{});
}
function loop() {
  if (!landmarker || !stream) return;
  if (video.readyState >= 2 && video.currentTime !== lastVideoTime) {
    lastVideoTime = video.currentTime;
    const result = landmarker.detectForVideo(video, performance.now());
    const points = result.landmarks?.[0];
    if (points) {
      handWasVisible = true;
      draw(points);
      const count = fingerCount(points);
      const candidate = gestureName(count);
      $("finger-label").textContent = "Fingers: " + count;
      $("gesture-result").textContent = "Gesture: " + candidate;
      if (candidate !== "UNKNOWN") {
        history.push(candidate); if (history.length > 5) history.shift();
        if (history.length === 5 && history.filter(x => x === candidate).length >= 4 && candidate !== lastGesture) {
          lastGesture = candidate; postGesture(candidate, count);
        }
      } else { history = []; }
    } else {
      draw(null); history = []; lastGesture = null;
      $("finger-label").textContent = "Fingers: 0";
      $("gesture-result").textContent = "Gesture: NO HAND";
      if (handWasVisible) { postRelease(); handWasVisible = false; }
    }
  }
  raf = requestAnimationFrame(loop);
}
async function startCamera() {
  const button = $("camera-toggle"); button.disabled = true;
  $("camera-help").textContent = "Loading hand recognition model…";
  try {
    if (!navigator.mediaDevices?.getUserMedia) throw new Error("Camera access requires HTTPS or localhost.");
    const vision = await FilesetResolver.forVisionTasks("https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21/wasm");
    landmarker = await HandLandmarker.createFromOptions(vision, {
      baseOptions: {modelAssetPath:"https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",delegate:"CPU"},
      runningMode:"VIDEO", numHands:1, minHandDetectionConfidence:.65, minHandPresenceConfidence:.65, minTrackingConfidence:.6
    });
    stream = await navigator.mediaDevices.getUserMedia({video:{facingMode:"user",width:{ideal:640},height:{ideal:480}},audio:false});
    video.srcObject = stream; await video.play();
    button.textContent = "Stop camera"; $("camera-status").textContent = "CONNECTED";
    $("camera-help").textContent = "Camera active. Video is processed locally in this browser.";
    loop();
  } catch (error) {
    $("camera-help").textContent = "Camera error: " + error.message;
    $("camera-status").textContent = "NOT CONNECTED";
    if (stream) stream.getTracks().forEach(t=>t.stop());
    stream = null; if (landmarker) landmarker.close(); landmarker = null;
  } finally { button.disabled = false; }
}
function stopCamera() {
  if (raf) cancelAnimationFrame(raf);
  if (stream) stream.getTracks().forEach(t=>t.stop());
  if (landmarker) landmarker.close();
  stream = null; landmarker = null; video.srcObject = null; draw(null);
  history=[]; lastGesture=null; handWasVisible=false; $("camera-toggle").textContent="Start camera";
  $("camera-status").textContent="NOT STARTED"; $("gesture-result").textContent="Gesture: NO HAND";
  $("finger-label").textContent="Fingers: 0"; $("camera-help").textContent="Camera stopped.";
  postRelease();
}
$("camera-toggle").addEventListener("click",()=>stream?stopCamera():startCamera());

function canvasSetup(id) {
  const el=$(id), w=el.clientWidth||400, h=Number(el.getAttribute("height"))||120, d=window.devicePixelRatio||1;
  el.width=w*d; el.height=h*d; const c=el.getContext("2d"); c.setTransform(d,0,0,d,0,0); return {c,w,h};
}
function lineChart(id,values,color,suffix="") {
  const {c,w,h}=canvasSetup(id),l=10,r=w-10,t=12,b=h-20;
  c.clearRect(0,0,w,h); c.strokeStyle="#263750";
  for(let i=0;i<4;i++){const y=t+i*(b-t)/3;c.beginPath();c.moveTo(l,y);c.lineTo(r,y);c.stroke();}
  if(!values.length)return; const min=Math.min(0,...values),max=Math.max(10,...values),range=Math.max(1,max-min);
  const pts=values.map((v,i)=>({x:l+i*(r-l)/Math.max(1,values.length-1),y:b-(v-min)/range*(b-t)}));
  c.beginPath();pts.forEach((p,i)=>i?c.lineTo(p.x,p.y):c.moveTo(p.x,p.y));c.strokeStyle=color;c.lineWidth=2.5;c.stroke();
  c.fillStyle="#8294ad";c.font="9px sans-serif";c.fillText(values.at(-1)+suffix,Math.max(10,r-40),10);
}
function barChart(items) {
  const {c,w,h}=canvasSetup("production-chart");c.clearRect(0,0,w,h);
  if(!items.length){c.fillStyle="#8294ad";c.font="10px sans-serif";c.fillText("No gesture activity recorded yet.",10,30);return;}
  const data=items.slice(-8),max=Math.max(1,...data.map(x=>x.total)),gap=9,bw=(w-20-gap*(data.length-1))/data.length;
  data.forEach((x,i)=>{const bh=x.total/max*(h-32),bx=10+i*(bw+gap),by=h-21-bh;c.fillStyle="#58d7cd";c.fillRect(bx,by,bw,bh);c.fillStyle="#8294ad";c.font="8px sans-serif";c.textAlign="center";c.fillText(x.hour,bx+bw/2,h-5);});c.textAlign="left";
}
function showActivity(items) {
  $("activity-list").innerHTML=items.length?items.map(x=>'<div class="activity-item"><span class="activity-time">'+x.created_at.slice(11,19)+'</span><span class="activity-message"><b>'+x.gesture+'</b><small>'+x.username+' · '+x.machine_status+'</small></span></div>').join(""):'<div class="empty-state">No gesture activity recorded yet.</div>';
}
function showAlerts(items) {
  $("alert-list").innerHTML=items.length?items.map(x=>'<div class="alert-row '+x.severity+'"><span class="alert-mark">'+(x.severity==="danger"?"!":"△")+'</span><div><b>'+x.message+'</b><small>'+x.time+' · Demo notification</small></div></div>').join(""):'<div class="empty-state">✓ No active demo alerts.</div>';
}
async function refresh() {
  try {
    const response=await fetch("/api/status",{cache:"no-store"});
    if(response.status===401){location.href="/login";return;}
    const d=await response.json();
    $("clock").textContent=d.clock;$("machine-status").textContent=d.machine_status;$("mode-label").textContent="Mode: "+d.mode;
    $("production-events").textContent=d.production_events;$("efficiency").textContent=d.efficiency;$("chart-current").textContent=d.efficiency+"%";
    $("efficiency-bar").style.width=d.efficiency+"%";$("gesture-label").textContent="Gesture: "+d.gesture;
    $("temperature").textContent=Number(d.temperature).toFixed(1);$("pressure").textContent=Number(d.pressure).toFixed(2);$("vibration").textContent=Number(d.vibration).toFixed(2);
    $("temperature-bar").style.width=Math.min(100,d.temperature/90*100)+"%";$("pressure-bar").style.width=Math.min(100,d.pressure/10*100)+"%";$("vibration-bar").style.width=Math.min(100,d.vibration/6*100)+"%";
    const color=d.machine_status==="RUNNING"?"#45d6a0":d.machine_status==="PAUSED"?"#f1b95d":"#ff777f";
    $("machine-status").style.color=color;$("status-dot").style.background=color;$("machine-model-status").textContent=d.machine_status;
    $("machine-model").classList.toggle("running",d.machine_status==="RUNNING");
    $("machine-model").classList.toggle("paused",d.machine_status==="PAUSED");
    showActivity(d.activity||[]);showAlerts(d.alerts||[]);
    const a=await(await fetch("/api/analytics")).json();
    const samples=a.sensors||[];lineChart("efficiency-chart",samples.map(x=>x.efficiency),"#58d7cd","%");
    barChart(a.production_by_hour||[]);
  } catch(error) { $("camera-status").textContent="SERVER OFFLINE"; }
}
$("clear-alerts").addEventListener("click",async()=>{await fetch("/api/clear-alerts",{method:"POST"});showAlerts([]);});
refresh();setInterval(refresh,2000);
window.addEventListener("resize",()=>refresh());
