import socket
import json
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

ANEMO_HOST = "127.0.0.1"
ANEMO_PORT = 8080

def fetch_stats_from_cpp():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect((ANEMO_HOST, ANEMO_PORT))

            payload = "STATS_JSON\n<EOQ>\n"
            s.sendall(payload.encode("utf-8"))

            raw_res = b""

            while b"<EOQ>" not in raw_res:
                chunk = s.recv(1024)
                if not chunk:
                    break
                raw_res += chunk

            text = (
                raw_res
                .decode("utf-8", errors="replace")
                .replace("<EOQ>", "")
                .strip()
            )

            data = json.loads(text)
            data["connected"] = True

            return data

    except Exception as e:
        return {
            "error": str(e),
            "connected": False
        }


HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Anemo DB • Server Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
    <style>
        * {
            box-sizing: border-box;
        }

        /* Default Dark Theme Variables */
        :root {
            --bg: #070b14;
            --panel: #0d1424;
            --panel-light: #111b2e;
            --border: #1d2a42;
            --text: #e6edf7;
            --muted: #7f8da5;
            
            --glow1: rgba(91, 156, 255, 0.09);
            --glow2: rgba(155, 124, 255, 0.07);
            
            --blue: #5b9cff;
            --cyan: #4dd9ff;
            --green: #39d98a;
            --red: #ff5c70;
            --yellow: #f7c65b;
            --purple: #9b7cff;
            
            --shadow: 0 10px 35px rgba(0, 0, 0, 0.30);
            --chart-text: #e6edf7;
            --chart-muted: #7f8da5;
            --grid-color: rgba(127, 141, 165, 0.12);
        }

        /* Light Theme Overrides */
        [data-theme="light"] {
            --bg: #f1f5f9;
            --panel: #ffffff;
            --panel-light: #f8fafc;
            --border: #e2e8f0;
            --text: #0f172a;
            --muted: #64748b;
            
            --glow1: rgba(91, 156, 255, 0.04);
            --glow2: rgba(155, 124, 255, 0.03);
            
            --blue: #2563eb;
            --cyan: #06b6d4;
            --green: #16a34a;
            --red: #dc2626;
            --yellow: #d97706;
            --purple: #7c3aed;
            
            --shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
            --chart-text: #1e293b;
            --chart-muted: #64748b;
            --grid-color: rgba(0, 0, 0, 0.06);
        }

        body {
            margin: 0;
            min-height: 100vh;
            background:
                radial-gradient(circle at 15% 10%, var(--glow1), transparent 30%),
                radial-gradient(circle at 85% 20%, var(--glow2), transparent 28%),
                var(--bg);
            color: var(--text);
            font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            transition: background 0.3s ease, color 0.3s ease;
        }

        /* ───────── Header ───────── */
        .header {
            max-width: 1400px;
            margin: auto;
            padding: 30px 28px 22px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 20px;
        }
        .brand { display: flex; align-items: center; gap: 16px; }
        .logo {
            width: 48px; height: 48px;
            display: flex; align-items: center; justify-content: center;
            border-radius: 14px;
            background: linear-gradient(135deg, #5b9cff, #8a6cff);
            color: white; font-size: 22px; font-weight: 800;
            box-shadow: 0 8px 25px rgba(91, 156, 255, 0.25);
        }
        .brand h1 { margin: 0; font-size: 23px; letter-spacing: -0.4px; }
        .brand p { margin: 4px 0 0; color: var(--muted); font-size: 13px; }

        .header-actions { display: flex; align-items: center; gap: 15px; }
        
        .theme-toggle {
            background: var(--panel-light);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 8px 14px;
            border-radius: 999px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
        }
        .theme-toggle:hover { background: var(--panel); border-color: var(--muted); }

        .status {
            display: flex; align-items: center; gap: 10px;
            padding: 9px 14px;
            border: 1px solid var(--border);
            border-radius: 999px;
            background: var(--panel);
            font-size: 13px; font-weight: 600;
        }
        .status-dot {
            width: 9px; height: 9px; border-radius: 50%;
            background: var(--yellow); box-shadow: 0 0 12px var(--yellow);
        }
        .online .status-dot { background: var(--green); box-shadow: 0 0 12px var(--green); }
        .offline .status-dot { background: var(--red); box-shadow: 0 0 12px var(--red); }

        /* ───────── Main & Panels ───────── */
        .container { max-width: 1400px; margin: auto; padding: 0 28px 40px; }

        .server-bar {
            display: flex; justify-content: space-between; align-items: center; gap: 20px;
            padding: 16px 20px; margin-bottom: 20px;
            background: var(--panel); border: 1px solid var(--border);
            border-radius: 14px; box-shadow: var(--shadow);
            transition: all 0.3s ease;
        }
        .server-info { display: flex; align-items: center; gap: 14px; }
        .server-label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
        .server-address { font-family: monospace; color: var(--cyan); font-size: 14px; }
        .updated { color: var(--muted); font-size: 12px; }

        .metrics {
            display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 15px; margin-bottom: 20px;
        }
        .metric {
            position: relative; overflow: hidden; padding: 19px;
            background: linear-gradient(145deg, var(--panel-light), var(--panel));
            border: 1px solid var(--border); border-radius: 14px; box-shadow: var(--shadow);
            transition: all 0.3s ease;
        }
        .metric::after {
            content: ""; position: absolute; width: 90px; height: 90px;
            right: -35px; bottom: -40px; border-radius: 50%;
            background: var(--accent); opacity: 0.07;
        }
        .metric-label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.7px; }
        .metric-value { margin-top: 9px; font-size: 27px; font-weight: 700; letter-spacing: -0.7px; color: var(--accent); }
        .metric-sub { margin-top: 5px; color: var(--muted); font-size: 11px; }

        .panel-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
        .panel {
            background: var(--panel); border: 1px solid var(--border);
            border-radius: 14px; padding: 20px; box-shadow: var(--shadow);
            transition: all 0.3s ease;
        }
        .panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .panel-title { font-size: 14px; font-weight: 650; }
        .panel-description { color: var(--muted); font-size: 11px; }
        .chart-container { height: 280px; position: relative; }

        .utilization { margin-top: 18px; padding-top: 18px; border-top: 1px solid var(--border); }
        .util-header { display: flex; justify-content: space-between; margin-bottom: 9px; font-size: 12px; }
        .util-header span:first-child { color: var(--muted); }
        .progress { width: 100%; height: 7px; background: var(--panel-light); border-radius: 10px; overflow: hidden; border: 1px solid var(--border); }
        .progress-bar {
            height: 100%; width: 0%; border-radius: inherit;
            background: linear-gradient(90deg, var(--blue), var(--purple)); transition: width 0.5s ease;
        }

        footer {
            max-width: 1400px; margin: 0 auto; padding: 8px 28px 25px;
            color: var(--muted); font-size: 11px; display: flex; justify-content: space-between;
        }

        @media (max-width: 1000px) { .metrics { grid-template-columns: repeat(2, 1fr); } .panel-grid { grid-template-columns: 1fr; } }
        @media (max-width: 600px) { .header, .server-bar { align-items: flex-start; flex-direction: column; } .metrics { grid-template-columns: 1fr; } .container, .header, footer { padding-left: 16px; padding-right: 16px; } }
    </style>
</head>

<body>
<header class="header">
    <div class="brand">
        <div class="logo">A</div>
        <div>
            <h1>Anemo DB</h1>
            <p>High-performance C++ multi-threaded LRU cache</p>
        </div>
    </div>
    <div class="header-actions">
        <button id="themeToggle" class="theme-toggle">☀️ Light</button>
        <div id="status" class="status">
            <span class="status-dot"></span>
            <span id="statusText">Connecting</span>
        </div>
    </div>
</header>

<main class="container">
    <div class="server-bar">
        <div class="server-info">
            <div>
                <div class="server-label">Anemo Instance</div>
                <div class="server-address">tcp://{{ host }}:{{ port }}</div>
            </div>
        </div>
        <div class="updated">
            Last update: <span id="lastUpdated">--</span>
        </div>
    </div>

    <section class="metrics">
        <div class="metric" style="--accent: var(--blue)"><div class="metric-label">Hit Rate</div><div class="metric-value" id="hitRate">0.0%</div><div class="metric-sub">Cache efficiency</div></div>
        <div class="metric" style="--accent: var(--cyan)"><div class="metric-label">Throughput</div><div class="metric-value" id="throughput">0.00</div><div class="metric-sub">requests / second</div></div>
        <div class="metric" style="--accent: var(--green)"><div class="metric-label">Avg Latency</div><div class="metric-value" id="avgLatency">0.00 ms</div><div class="metric-sub">request processing time</div></div>
        <div class="metric" style="--accent: var(--purple)"><div class="metric-label">Uptime</div><div class="metric-value" id="uptime">0s</div><div class="metric-sub">server runtime</div></div>
        <div class="metric" style="--accent: var(--yellow)"><div class="metric-label">Cache Entries</div><div class="metric-value" id="slotUsage">0 / 0</div><div class="metric-sub">occupied / capacity</div></div>
        <div class="metric" style="--accent: var(--green)"><div class="metric-label">Memory</div><div class="metric-value" id="memUsage">0 KB</div><div class="metric-sub">estimated footprint</div></div>
        <div class="metric" style="--accent: var(--blue)"><div class="metric-label">Total Requests</div><div class="metric-value" id="totalRequests">0</div><div class="metric-sub">requests processed</div></div>
        <div class="metric" style="--accent: var(--red)"><div class="metric-label">Queue</div><div class="metric-value" id="queue">0</div><div class="metric-sub">pending tasks</div></div>
    </section>

    <section class="panel-grid">
        <div class="panel">
            <div class="panel-header"><div><div class="panel-title">Cache Performance</div><div class="panel-description">Hit vs miss distribution</div></div></div>
            <div class="chart-container"><canvas id="hitMissChart"></canvas></div>
        </div>
        <div class="panel">
            <div class="panel-header"><div><div class="panel-title">Request Throughput</div><div class="panel-description">Recent requests per second</div></div></div>
            <div class="chart-container"><canvas id="throughputChart"></canvas></div>
        </div>
        <div class="panel">
            <div class="panel-header"><div><div class="panel-title">Cache Capacity</div><div class="panel-description">Current memory slot utilization</div></div></div>
            <div class="utilization">
                <div class="util-header"><span>Slots utilized</span><span id="utilText">0%</span></div>
                <div class="progress"><div id="utilBar" class="progress-bar"></div></div>
            </div>
        </div>
        <div class="panel">
            <div class="panel-header"><div><div class="panel-title">Request Summary</div><div class="panel-description">Current Anemo workload</div></div></div>
            <div class="utilization">
                <div class="util-header"><span>Cache Hits</span><strong id="hits">0</strong></div>
                <div class="util-header"><span>Cache Misses</span><strong id="misses">0</strong></div>
                <div class="util-header"><span>Directory Entries</span><strong id="directory">0</strong></div>
            </div>
        </div>
    </section>
</main>

<footer>
    <span>Anemo • Telemetry Console</span>
    <span>Auto-refresh: 2s</span>
</footer>

<script>
// Retrieve CSS Variables dynamically so Chart.js reacts to theme changes
function getCSSVar(name) { return getComputedStyle(document.body).getPropertyValue(name).trim(); }

/* ───────── Chart Initializations ───────── */
const hitMissChart = new Chart(document.getElementById("hitMissChart").getContext("2d"), {
    type: "doughnut",
    data: {
        labels: ["Cache Hits", "Cache Misses"],
        datasets: [{ data: [0, 0], backgroundColor: ["#39d98a", "#ff5c70"], borderWidth: 0, hoverOffset: 5 }]
    },
    options: {
        responsive: true, maintainAspectRatio: false, cutout: "72%",
        plugins: { legend: { position: "bottom", labels: { color: getCSSVar("--chart-text"), padding: 18, usePointStyle: true } } }
    }
});

const throughputChart = new Chart(document.getElementById("throughputChart").getContext("2d"), {
    type: "line",
    data: {
        labels: [],
        datasets: [{ label: "Requests / sec", data: [], borderColor: "#4dd9ff", backgroundColor: "rgba(77, 217, 255, 0.08)", fill: true, tension: 0.35, pointRadius: 2, pointHoverRadius: 5 }]
    },
    options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        scales: {
            x: { ticks: { color: getCSSVar("--chart-muted") }, grid: { color: getCSSVar("--grid-color") } },
            y: { beginAtZero: true, ticks: { color: getCSSVar("--chart-muted") }, grid: { color: getCSSVar("--grid-color") } }
        },
        plugins: { legend: { labels: { color: getCSSVar("--chart-text") } } }
    }
});


/* ───────── Theme Toggler Logic ───────── */
const themeToggle = document.getElementById("themeToggle");
themeToggle.addEventListener("click", () => {
    if (document.body.getAttribute("data-theme") === "light") {
        document.body.removeAttribute("data-theme");
        themeToggle.innerText = "☀️ Light";
    } else {
        document.body.setAttribute("data-theme", "light");
        themeToggle.innerText = "🌙 Dark";
    }
    
    // Force Chart.js to redraw text/grid lines with new theme colors
    hitMissChart.options.plugins.legend.labels.color = getCSSVar("--chart-text");
    hitMissChart.update();

    throughputChart.options.scales.x.ticks.color = getCSSVar("--chart-muted");
    throughputChart.options.scales.x.grid.color = getCSSVar("--grid-color");
    throughputChart.options.scales.y.ticks.color = getCSSVar("--chart-muted");
    throughputChart.options.scales.y.grid.color = getCSSVar("--grid-color");
    throughputChart.options.plugins.legend.labels.color = getCSSVar("--chart-text");
    throughputChart.update();
});


/* ───────── Helpers & Data Fetching ───────── */
function formatUptime(seconds) {
    if (seconds < 60) return seconds + "s";
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return minutes + "m";
    const hours = Math.floor(minutes / 60);
    return hours + "h " + (minutes % 60) + "m";
}

async function updateMetrics() {
    try {
        const response = await fetch("/api/stats");
        const data = await response.json();
        const status = document.getElementById("status");
        const statusText = document.getElementById("statusText");

        if (!data.connected) {
            status.className = "status offline";
            statusText.innerText = "OFFLINE";
            return;
        }

        status.className = "status online";
        statusText.innerText = "ONLINE";

        document.getElementById("hitRate").innerText = data.hit_rate.toFixed(1) + "%";
        document.getElementById("throughput").innerText = data.throughput.toFixed(2);
        document.getElementById("avgLatency").innerText = data.avg_latency_ms.toFixed(2) + " ms";
        document.getElementById("uptime").innerText = formatUptime(data.uptime_sec);
        document.getElementById("slotUsage").innerText = data.cache_lines + " / " + data.max_capacity;
        document.getElementById("memUsage").innerText = data.kb.toFixed(2) + " KB";
        document.getElementById("totalRequests").innerText = data.requests.toLocaleString();
        document.getElementById("queue").innerText = data.queue_length;
        document.getElementById("hits").innerText = data.hits.toLocaleString();
        document.getElementById("misses").innerText = data.misses.toLocaleString();
        document.getElementById("directory").innerText = data.directory_size;

        const utilization = data.max_capacity > 0 ? (data.cache_lines / data.max_capacity) * 100 : 0;
        document.getElementById("utilBar").style.width = Math.min(utilization, 100) + "%";
        document.getElementById("utilText").innerText = utilization.toFixed(1) + "%";

        hitMissChart.data.datasets[0].data = [data.hits, data.misses];
        hitMissChart.update();

        const now = new Date().toLocaleTimeString();
        if (throughputChart.data.labels.length >= 20) {
            throughputChart.data.labels.shift();
            throughputChart.data.datasets[0].data.shift();
        }
        throughputChart.data.labels.push(now);
        throughputChart.data.datasets[0].data.push(data.throughput);
        throughputChart.update();

        document.getElementById("lastUpdated").innerText = new Date().toLocaleTimeString();
    } catch (error) {
        document.getElementById("status").className = "status offline";
        document.getElementById("statusText").innerText = "CONNECTION ERROR";
    }
}

// Start loops
updateMetrics();
setInterval(updateMetrics, 2000);
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_PAGE, host=ANEMO_HOST, port=ANEMO_PORT)

@app.route("/api/stats")
def get_stats():
    return jsonify(fetch_stats_from_cpp())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)