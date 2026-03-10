"""
LiteWing Blackbox Viewer — Web-Based 3D Flight Analysis
=========================================================
Reads a CSV flight log and opens an interactive web dashboard in your browser.

Features:
    - 3D flight path with drone model (Three.js)
    - 3D attitude indicator (roll/pitch/yaw)
    - 2D charts: height, attitude, velocity+corrections, battery+commands (Plotly.js)
    - Synced timeline with play/pause/speed controls
    - Flight phase color coding
    - No server needed — fully self-contained HTML

Usage:
    python blackbox_viewer.py                        # default my_flight_log.csv
    python blackbox_viewer.py path/to/flight.csv     # custom log file
"""

import csv
import json
import sys
import os
import tempfile
import webbrowser


def load_csv(filepath):
    """Read a LiteWing CSV flight log into a dict of lists."""
    keys = [
        "time", "pos_x", "pos_y", "height", "range", "vx", "vy",
        "corr_vx", "corr_vy", "battery", "roll", "pitch", "yaw",
        "gyro_x", "gyro_y", "gyro_z", "phase", "target_h",
        "cmd_vx", "cmd_vy",
    ]
    data = {k: [] for k in keys}

    with open(filepath, "r") as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            if len(row) < 20:
                continue
            try:
                for i, key in enumerate(keys):
                    if key == "phase":
                        data[key].append(row[i].strip())
                    else:
                        data[key].append(float(row[i]))
            except (ValueError, IndexError):
                continue
    return data


# ═══════════════════════════════════════════════════════════════════
#  HTML TEMPLATE
# ═══════════════════════════════════════════════════════════════════

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LiteWing Blackbox Viewer</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<style>
:root {
    --bg-primary: #0f0f1a;
    --bg-secondary: #1a1a2e;
    --bg-panel: #16213e;
    --bg-glass: rgba(22, 33, 62, 0.85);
    --border: rgba(100, 120, 180, 0.2);
    --text: #cdd6f4;
    --text-dim: #6c7086;
    --cyan: #89dceb;
    --green: #a6e3a1;
    --red: #f38ba8;
    --yellow: #f9e2af;
    --blue: #89b4fa;
    --mauve: #cba6f7;
    --peach: #fab387;
    --teal: #94e2d5;
    --pink: #f5c2e7;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg-primary);
    color: var(--text);
    height: 100vh;
    display: grid;
    grid-template-rows: auto 1fr auto;
    overflow: hidden;
}

/* ── Header ─────────────────────────────────────────── */
.header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 20px;
    background: linear-gradient(135deg, var(--bg-secondary), var(--bg-panel));
    border-bottom: 1px solid var(--border);
}
.header h1 {
    font-size: 16px;
    font-weight: 700;
    background: linear-gradient(90deg, var(--cyan), var(--blue));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.header .stats {
    display: flex;
    gap: 20px;
    font-size: 12px;
    color: var(--text-dim);
}
.header .stats span { color: var(--cyan); font-weight: 600; }

/* ── Main layout ────────────────────────────────────── */
.main {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    padding: 8px;
    overflow: hidden;
}

/* ── 3D Panel ───────────────────────────────────────── */
.panel-3d {
    display: grid;
    grid-template-rows: 1fr auto;
    gap: 8px;
}
.three-container {
    background: var(--bg-glass);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    position: relative;
    backdrop-filter: blur(10px);
}
.three-container canvas { display: block; width: 100% !important; height: 100% !important; }
.three-label {
    position: absolute;
    top: 10px;
    left: 14px;
    font-size: 11px;
    font-weight: 700;
    color: var(--cyan);
    text-shadow: 0 0 10px rgba(137, 220, 235, 0.5);
}
.attitude-box {
    background: var(--bg-glass);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 10px 16px;
    display: flex;
    justify-content: space-around;
    align-items: center;
    gap: 12px;
    backdrop-filter: blur(10px);
}
.att-item {
    text-align: center;
    font-size: 11px;
}
.att-item .label { color: var(--text-dim); font-size: 9px; text-transform: uppercase; letter-spacing: 1px; }
.att-item .value { font-size: 18px; font-weight: 700; font-variant-numeric: tabular-nums; }
.att-item.roll .value { color: var(--red); }
.att-item.pitch .value { color: var(--green); }
.att-item.yaw .value { color: var(--yellow); }
.att-item.height .value { color: var(--cyan); }
.att-item.battery .value { color: var(--green); }
.att-item.phase .value { color: var(--mauve); font-size: 13px; }

/* ── Charts Panel ───────────────────────────────────── */
.charts-container {
    display: grid;
    grid-template-rows: repeat(4, 1fr);
    gap: 6px;
    overflow: hidden;
}
.chart-panel {
    background: var(--bg-glass);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
    backdrop-filter: blur(10px);
}
.chart-panel .js-plotly-plot, .chart-panel .plotly { height: 100% !important; }

/* ── Timeline ───────────────────────────────────────── */
.timeline {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 20px;
    background: linear-gradient(135deg, var(--bg-secondary), var(--bg-panel));
    border-top: 1px solid var(--border);
}
.timeline button {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 6px 14px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 13px;
    transition: all 0.2s;
}
.timeline button:hover { background: rgba(137, 220, 235, 0.15); border-color: var(--cyan); }
.timeline button.active { background: rgba(137, 220, 235, 0.2); border-color: var(--cyan); color: var(--cyan); }
.timeline input[type="range"] {
    flex: 1;
    height: 6px;
    -webkit-appearance: none;
    appearance: none;
    background: var(--bg-panel);
    border-radius: 3px;
    outline: none;
    cursor: pointer;
}
.timeline input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 16px; height: 16px;
    background: var(--cyan);
    border-radius: 50%;
    box-shadow: 0 0 8px rgba(137, 220, 235, 0.5);
    cursor: pointer;
}
.timeline .time-display {
    font-size: 13px;
    font-variant-numeric: tabular-nums;
    min-width: 120px;
    text-align: center;
    color: var(--cyan);
    font-weight: 600;
}
.speed-select {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 12px;
}
</style>
</head>
<body>

<!-- Header -->
<div class="header">
    <h1>🛸 LiteWing Blackbox Viewer</h1>
    <div class="stats">
        <div>Duration: <span id="stat-duration">--</span></div>
        <div>Points: <span id="stat-points">--</span></div>
        <div>Max Drift: <span id="stat-drift">--</span></div>
    </div>
</div>

<!-- Main -->
<div class="main">
    <!-- Left: 3D View + Attitude -->
    <div class="panel-3d">
        <div class="three-container" id="three-canvas">
            <div class="three-label">3D Flight Path</div>
        </div>
        <div class="attitude-box">
            <div class="att-item phase"><div class="label">Phase</div><div class="value" id="att-phase">--</div></div>
            <div class="att-item roll"><div class="label">Roll</div><div class="value" id="att-roll">0.0°</div></div>
            <div class="att-item pitch"><div class="label">Pitch</div><div class="value" id="att-pitch">0.0°</div></div>
            <div class="att-item yaw"><div class="label">Yaw</div><div class="value" id="att-yaw">0.0°</div></div>
            <div class="att-item height"><div class="label">Height</div><div class="value" id="att-height">0.00m</div></div>
            <div class="att-item battery"><div class="label">Battery</div><div class="value" id="att-bat">0.0V</div></div>
        </div>
    </div>

    <!-- Right: Charts -->
    <div class="charts-container">
        <div class="chart-panel" id="chart-height"></div>
        <div class="chart-panel" id="chart-attitude"></div>
        <div class="chart-panel" id="chart-velocity"></div>
        <div class="chart-panel" id="chart-battery"></div>
    </div>
</div>

<!-- Timeline -->
<div class="timeline">
    <button id="btn-play" title="Play/Pause">▶</button>
    <select class="speed-select" id="speed-select">
        <option value="0.25">0.25×</option>
        <option value="0.5">0.5×</option>
        <option value="1" selected>1×</option>
        <option value="2">2×</option>
        <option value="4">4×</option>
    </select>
    <input type="range" id="timeline-slider" min="0" max="1000" value="0" step="1">
    <div class="time-display" id="time-display">0.000s / 0.000s</div>
</div>

<script>
// ═══════════════════════════════════════════════════════════════
//  DATA (injected by Python)
// ═══════════════════════════════════════════════════════════════
const D = __FLIGHT_DATA__;

const maxTime = D.time[D.time.length - 1];
const N = D.time.length;
let currentIdx = 0;
let playing = false;
let playSpeed = 1;
let lastFrameTime = 0;

// ═══════════════════════════════════════════════════════════════
//  STATS
// ═══════════════════════════════════════════════════════════════
document.getElementById('stat-duration').textContent = maxTime.toFixed(1) + 's';
document.getElementById('stat-points').textContent = N.toLocaleString();
const maxDrift = Math.max(
    Math.max(...D.pos_x.map(Math.abs)),
    Math.max(...D.pos_y.map(Math.abs))
).toFixed(3) + 'm';
document.getElementById('stat-drift').textContent = maxDrift;

// ═══════════════════════════════════════════════════════════════
//  UTILITY: find closest index for a given time
// ═══════════════════════════════════════════════════════════════
function timeToIndex(t) {
    t = Math.max(D.time[0], Math.min(t, maxTime));
    let lo = 0, hi = N - 1;
    while (lo < hi) {
        const mid = (lo + hi) >> 1;
        if (D.time[mid] < t) lo = mid + 1; else hi = mid;
    }
    return lo;
}

// ═══════════════════════════════════════════════════════════════
//  THREE.JS — 3D Scene
// ═══════════════════════════════════════════════════════════════
const container = document.getElementById('three-canvas');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0f0f1a);
scene.fog = new THREE.FogExp2(0x0f0f1a, 0.3);

const camera = new THREE.PerspectiveCamera(50, 1, 0.01, 100);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
container.appendChild(renderer.domElement);

const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.maxPolarAngle = Math.PI * 0.85;

// Scale factor: drone moves ~0.2m, we scale up for visibility
const SCALE = 3.0;

// Lighting
scene.add(new THREE.AmbientLight(0x4466aa, 0.5));
const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(2, 5, 3);
scene.add(dirLight);
scene.add(new THREE.HemisphereLight(0x89dceb, 0x1a1a2e, 0.3));

// Ground grid
const gridHelper = new THREE.GridHelper(4, 20, 0x3a3a5c, 0x2a2a3d);
scene.add(gridHelper);

// Axis indicators
function makeAxis(dir, color, len) {
    const mat = new THREE.LineBasicMaterial({ color });
    const pts = [new THREE.Vector3(0, 0, 0), dir.clone().multiplyScalar(len)];
    const geom = new THREE.BufferGeometry().setFromPoints(pts);
    return new THREE.Line(geom, mat);
}
scene.add(makeAxis(new THREE.Vector3(0, 0, -1), 0xa6e3a1, 0.6)); // Forward = -Z (green)
scene.add(makeAxis(new THREE.Vector3(-1, 0, 0), 0xf38ba8, 0.4)); // Left = -X (red)
scene.add(makeAxis(new THREE.Vector3(0, 1, 0), 0x89dceb, 0.4));  // Up = +Y (cyan)

// Flight path line — map drone coords to Three.js:
//   Three.js X = -Drone Y (so +left = screen left when viewed from default angle)
//   Three.js Y = Height
//   Three.js Z = -Drone X (so +forward = into screen, viewed from behind)
const phaseColors = {
    TAKEOFF: 0xa6e3a1, HOVER: 0x89dceb, HOVERING: 0x89dceb,
    LANDING: 0xf38ba8, STABILIZE: 0xf9e2af, MOVE: 0x89b4fa,
    WAYPOINT: 0xcba6f7, MANUAL: 0xfab387
};

const pathPositions = [];
const pathColors = [];
for (let i = 0; i < N; i++) {
    const x3d = -D.pos_y[i] * SCALE;
    const y3d = D.height[i] * SCALE;
    const z3d = -D.pos_x[i] * SCALE;
    pathPositions.push(x3d, y3d, z3d);
    const c = new THREE.Color(phaseColors[D.phase[i]] || 0x89dceb);
    pathColors.push(c.r, c.g, c.b);
}

const pathGeom = new THREE.BufferGeometry();
pathGeom.setAttribute('position', new THREE.Float32BufferAttribute(pathPositions, 3));
pathGeom.setAttribute('color', new THREE.Float32BufferAttribute(pathColors, 3));
const pathMat = new THREE.LineBasicMaterial({ vertexColors: true, linewidth: 2 });
const pathLine = new THREE.Line(pathGeom, pathMat);
scene.add(pathLine);

// Ground shadow (XZ projection)
const shadowPositions = [];
for (let i = 0; i < N; i++) {
    shadowPositions.push(-D.pos_y[i] * SCALE, 0.001, -D.pos_x[i] * SCALE);
}
const shadowGeom = new THREE.BufferGeometry();
shadowGeom.setAttribute('position', new THREE.Float32BufferAttribute(shadowPositions, 3));
const shadowMat = new THREE.LineBasicMaterial({ color: 0x3a3a5c, linewidth: 1 });
scene.add(new THREE.Line(shadowGeom, shadowMat));

// Vertical drop line (current pos to ground)
const dropGeom = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, 0)
]);
const dropLine = new THREE.Line(dropGeom, new THREE.LineDashedMaterial({
    color: 0x89dceb, dashSize: 0.03, gapSize: 0.02
}));
dropLine.computeLineDistances();
scene.add(dropLine);

// Start/End markers
function makeMarker(idx, color, size) {
    const geom = new THREE.SphereGeometry(size, 12, 12);
    const mat = new THREE.MeshPhongMaterial({ color, emissive: color, emissiveIntensity: 0.3 });
    const mesh = new THREE.Mesh(geom, mat);
    mesh.position.set(
        -D.pos_y[idx] * SCALE,
        D.height[idx] * SCALE,
        -D.pos_x[idx] * SCALE
    );
    return mesh;
}
scene.add(makeMarker(0, 0xa6e3a1, 0.03));       // start = green
scene.add(makeMarker(N - 1, 0xf38ba8, 0.03));   // end = red

// ── Drone Model ────────────────────────────────────
function createDroneModel() {
    const group = new THREE.Group();
    const bodyMat = new THREE.MeshPhongMaterial({ color: 0x89dceb, emissive: 0x89dceb, emissiveIntensity: 0.2 });
    const armMat = new THREE.MeshPhongMaterial({ color: 0xa6adc8 });
    const motorMat = new THREE.MeshPhongMaterial({ color: 0xf9e2af, emissive: 0xf9e2af, emissiveIntensity: 0.4 });
    const noseMat = new THREE.MeshPhongMaterial({ color: 0xa6e3a1, emissive: 0xa6e3a1, emissiveIntensity: 0.5 });

    // Center body
    group.add(new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.012, 0.04), bodyMat));

    // Arms
    const armLen = 0.1, armW = 0.008;
    for (const angle of [Math.PI / 4, -Math.PI / 4, 3 * Math.PI / 4, -3 * Math.PI / 4]) {
        const arm = new THREE.Mesh(new THREE.BoxGeometry(armLen, 0.005, armW), armMat);
        arm.rotation.y = angle;
        group.add(arm);

        // Motor at arm tip
        const motor = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.008, 8), motorMat);
        motor.position.set(
            Math.cos(angle) * armLen / 2,
            0.006,
            -Math.sin(angle) * armLen / 2
        );
        group.add(motor);
    }

    // Nose direction indicator (forward = -Z in model space)
    const nose = new THREE.Mesh(new THREE.ConeGeometry(0.01, 0.03, 4), noseMat);
    nose.rotation.x = Math.PI / 2;
    nose.position.z = -0.035;
    group.add(nose);

    return group;
}

const droneModel = createDroneModel();
scene.add(droneModel);

// Camera position — behind and above, looking at center
const cx = -D.pos_y[0] * SCALE;
const cy = D.height[0] * SCALE + 0.5;
const cz = -D.pos_x[0] * SCALE;
camera.position.set(cx + 0.8, cy + 0.8, cz + 0.8);
controls.target.set(cx, cy * 0.5, cz);

// ═══════════════════════════════════════════════════════════════
//  PLOTLY CHARTS
// ═══════════════════════════════════════════════════════════════
const plotlyLayout = {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(26,26,46,0.5)',
    font: { color: '#a6adc8', size: 9 },
    margin: { l: 45, r: 10, t: 25, b: 20 },
    xaxis: { gridcolor: '#3a3a5c', zerolinecolor: '#444466', showticklabels: true },
    yaxis: { gridcolor: '#3a3a5c', zerolinecolor: '#444466' },
    legend: { x: 1, xanchor: 'right', y: 1, font: { size: 8 }, bgcolor: 'rgba(0,0,0,0)' },
    shapes: [],
};
const plotlyConfig = { displayModeBar: false, responsive: true };

function cursorShape(t) {
    return {
        type: 'line', x0: t, x1: t, y0: 0, y1: 1, yref: 'paper',
        line: { color: 'rgba(137,220,235,0.7)', width: 1.5, dash: 'dot' }
    };
}

// Height chart
Plotly.newPlot('chart-height', [
    { x: D.time, y: D.height, name: 'Filtered', line: { color: '#89dceb', width: 1.5 } },
    { x: D.time, y: D.range, name: 'Raw ToF', line: { color: '#fab387', width: 1 }, opacity: 0.6 },
    { x: D.time, y: D.target_h, name: 'Target', line: { color: '#f38ba8', width: 1.2, dash: 'dash' } },
], { ...plotlyLayout, title: { text: 'Height (m)', font: { size: 11, color: '#89dceb' } },
     shapes: [cursorShape(0)] }, plotlyConfig);

// Attitude chart
Plotly.newPlot('chart-attitude', [
    { x: D.time, y: D.roll, name: 'Roll', line: { color: '#f38ba8', width: 1.2 } },
    { x: D.time, y: D.pitch, name: 'Pitch', line: { color: '#a6e3a1', width: 1.2 } },
    { x: D.time, y: D.yaw, name: 'Yaw', line: { color: '#f9e2af', width: 1.2 } },
], { ...plotlyLayout, title: { text: 'Attitude (°)', font: { size: 11, color: '#89dceb' } },
     shapes: [cursorShape(0)] }, plotlyConfig);

// Velocity + Corrections
Plotly.newPlot('chart-velocity', [
    { x: D.time, y: D.vx, name: 'VX (fwd)', line: { color: '#89b4fa', width: 1.3 } },
    { x: D.time, y: D.vy, name: 'VY (lat)', line: { color: '#cba6f7', width: 1.3 } },
    { x: D.time, y: D.corr_vx, name: 'Corr VX', line: { color: '#94e2d5', width: 1, dash: 'dash' } },
    { x: D.time, y: D.corr_vy, name: 'Corr VY', line: { color: '#f5c2e7', width: 1, dash: 'dash' } },
], { ...plotlyLayout, title: { text: 'Velocity & Corrections (m/s)', font: { size: 11, color: '#89dceb' } },
     shapes: [cursorShape(0)] }, plotlyConfig);

// Battery + Commands
Plotly.newPlot('chart-battery', [
    { x: D.time, y: D.battery, name: 'Battery (V)', line: { color: '#a6e3a1', width: 2 }, yaxis: 'y' },
    { x: D.time, y: D.cmd_vx, name: 'Cmd VX', line: { color: '#89b4fa', width: 1, dash: 'dot' }, yaxis: 'y2' },
    { x: D.time, y: D.cmd_vy, name: 'Cmd VY', line: { color: '#cba6f7', width: 1, dash: 'dot' }, yaxis: 'y2' },
], { ...plotlyLayout,
     title: { text: 'Battery & Commands', font: { size: 11, color: '#89dceb' } },
     yaxis: { ...plotlyLayout.yaxis, title: { text: 'V', font: { size: 9 } } },
     yaxis2: { overlaying: 'y', side: 'right', gridcolor: 'transparent',
               title: { text: 'm/s', font: { size: 9 } }, font: { color: '#a6adc8' } },
     shapes: [cursorShape(0)],
}, plotlyConfig);

// ═══════════════════════════════════════════════════════════════
//  UPDATE FUNCTION — syncs everything to a time value
// ═══════════════════════════════════════════════════════════════
function updateAll(idx) {
    if (idx < 0) idx = 0;
    if (idx >= N) idx = N - 1;
    currentIdx = idx;

    const t = D.time[idx];

    // ── Update 3D Drone ──
    const x3d = -D.pos_y[idx] * SCALE;
    const y3d = D.height[idx] * SCALE;
    const z3d = -D.pos_x[idx] * SCALE;
    droneModel.position.set(x3d, y3d, z3d);

    // Apply attitude (convert degrees to radians)
    droneModel.rotation.set(0, 0, 0);
    droneModel.rotation.order = 'YXZ';
    droneModel.rotation.x = THREE.MathUtils.degToRad(-D.pitch[idx]); // pitch = tilt forward
    droneModel.rotation.z = THREE.MathUtils.degToRad(-D.roll[idx]);  // roll = tilt sideways
    droneModel.rotation.y = THREE.MathUtils.degToRad(-D.yaw[idx]);   // yaw = rotate

    // Drop line
    const dp = dropLine.geometry.attributes.position;
    dp.setXYZ(0, x3d, y3d, z3d);
    dp.setXYZ(1, x3d, 0, z3d);
    dp.needsUpdate = true;
    dropLine.computeLineDistances();

    // ── Update Plotly cursors ──
    const shape = [cursorShape(t)];
    Plotly.relayout('chart-height', { shapes: shape });
    Plotly.relayout('chart-attitude', { shapes: shape });
    Plotly.relayout('chart-velocity', { shapes: shape });
    Plotly.relayout('chart-battery', { shapes: shape });

    // ── Update info display ──
    document.getElementById('att-roll').textContent = D.roll[idx].toFixed(1) + '°';
    document.getElementById('att-pitch').textContent = D.pitch[idx].toFixed(1) + '°';
    document.getElementById('att-yaw').textContent = D.yaw[idx].toFixed(1) + '°';
    document.getElementById('att-height').textContent = D.height[idx].toFixed(3) + 'm';
    document.getElementById('att-bat').textContent = D.battery[idx].toFixed(2) + 'V';
    document.getElementById('att-phase').textContent = D.phase[idx];

    // ── Update timeline ──
    const slider = document.getElementById('timeline-slider');
    slider.value = (t / maxTime) * 1000;
    document.getElementById('time-display').textContent =
        t.toFixed(3) + 's / ' + maxTime.toFixed(1) + 's';
}

// ═══════════════════════════════════════════════════════════════
//  PLAYBACK CONTROLS
// ═══════════════════════════════════════════════════════════════
const btnPlay = document.getElementById('btn-play');
const slider = document.getElementById('timeline-slider');
const speedSelect = document.getElementById('speed-select');

btnPlay.addEventListener('click', () => {
    playing = !playing;
    btnPlay.textContent = playing ? '⏸' : '▶';
    btnPlay.classList.toggle('active', playing);
    if (playing) lastFrameTime = performance.now();
});

slider.addEventListener('input', () => {
    const t = (slider.value / 1000) * maxTime;
    updateAll(timeToIndex(t));
});

speedSelect.addEventListener('change', () => {
    playSpeed = parseFloat(speedSelect.value);
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.code === 'Space') { e.preventDefault(); btnPlay.click(); }
    else if (e.code === 'ArrowLeft') updateAll(Math.max(0, currentIdx - 10));
    else if (e.code === 'ArrowRight') updateAll(Math.min(N - 1, currentIdx + 10));
    else if (e.code === 'Home') updateAll(0);
    else if (e.code === 'End') updateAll(N - 1);
});

// ═══════════════════════════════════════════════════════════════
//  ANIMATION LOOP
// ═══════════════════════════════════════════════════════════════
function resizeAll() {
    const rect = container.getBoundingClientRect();
    camera.aspect = rect.width / rect.height;
    camera.updateProjectionMatrix();
    renderer.setSize(rect.width, rect.height);
}

window.addEventListener('resize', () => {
    resizeAll();
    Plotly.Plots.resize('chart-height');
    Plotly.Plots.resize('chart-attitude');
    Plotly.Plots.resize('chart-velocity');
    Plotly.Plots.resize('chart-battery');
});

function animate(timestamp) {
    requestAnimationFrame(animate);

    // Playback
    if (playing) {
        const dt = (timestamp - lastFrameTime) / 1000;
        lastFrameTime = timestamp;
        const currentTime = D.time[currentIdx] + dt * playSpeed;
        if (currentTime >= maxTime) {
            playing = false;
            btnPlay.textContent = '▶';
            btnPlay.classList.remove('active');
            updateAll(N - 1);
        } else {
            updateAll(timeToIndex(currentTime));
        }
    }

    controls.update();
    renderer.render(scene, camera);
}

// Initialize
resizeAll();
updateAll(0);
requestAnimationFrame(animate);
</script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════
#  MAIN — Read CSV, build HTML, open browser
# ═══════════════════════════════════════════════════════════════════

def main():
    # Resolve file path
    default_log = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "..", "..", "my_flight_log.csv"
    ))

    if len(sys.argv) > 1:
        log_path = sys.argv[1]
    elif os.path.exists(default_log):
        log_path = default_log
    else:
        print("Usage: python blackbox_viewer.py [path/to/flight_log.csv]")
        print(f"  Default not found: {default_log}")
        sys.exit(1)

    if not os.path.exists(log_path):
        print(f"Error: File not found: {log_path}")
        sys.exit(1)

    print(f"Loading: {log_path}")
    data = load_csv(log_path)
    print(f"  {len(data['time'])} data points, {data['time'][-1]:.1f}s")
    print(f"  Phases: {' → '.join(dict.fromkeys(data['phase']))}")

    # Build HTML
    json_data = json.dumps(data)
    html = HTML_TEMPLATE.replace("__FLIGHT_DATA__", json_data)

    # Write to temp file
    tmp = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8")
    tmp.write(html)
    tmp.close()

    print(f"Opening in browser...")
    webbrowser.open("file:///" + tmp.name.replace("\\", "/"))
    print(f"  HTML saved: {tmp.name}")
    print(f"\nKeyboard shortcuts:")
    print(f"  Space      — Play/Pause")
    print(f"  ← →        — Step backward/forward")
    print(f"  Home/End   — Jump to start/end")


if __name__ == "__main__":
    main()
