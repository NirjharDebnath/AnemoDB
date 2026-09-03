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

// Dynamic Comparison Chart
const latencyComparisonChart = new Chart(document.getElementById("latencyComparisonChart").getContext("2d"), {
    type: "line",
    data: {
        labels: [],
        datasets: [
            { label: "Cache Latency (ms)", data: [], borderColor: "#39d98a", backgroundColor: "transparent", tension: 0.3, pointRadius: 2 },
            { label: "PostgreSQL Latency (ms)", data: [], borderColor: "#ff5c70", backgroundColor: "transparent", tension: 0.3, pointRadius: 2 }
        ]
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

/* ───────── Simulation Controls ───────── */
let isSimulating = false;
const simToggleBtn = document.getElementById("simToggleBtn");
const simTarget = document.getElementById("simTarget");
const threadSlider = document.getElementById("threadSlider");
const threadVal = document.getElementById("threadVal");

threadSlider.addEventListener("input", (e) => {
    threadVal.innerText = e.target.value;
    if (isSimulating) sendSimControl(true);
});

simTarget.addEventListener("change", () => {
    if (isSimulating) sendSimControl(true);
});

simToggleBtn.addEventListener("click", () => {
    isSimulating = !isSimulating;
    sendSimControl(isSimulating);
});

async function sendSimControl(running) {
    try {
        const res = await fetch("/api/traffic/control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                running: running,
                mode: simTarget.value,
                threads: parseInt(threadSlider.value)
            })
        });
        const data = await res.json();
        isSimulating = data.running;
        simToggleBtn.innerText = isSimulating ? "⏹ Stop Load" : "▶ Start Load";
        simToggleBtn.style.background = isSimulating ? "var(--red)" : "var(--blue)";
    } catch (e) {
        console.error("Traffic control error:", e);
    }
}

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
    
    [hitMissChart, throughputChart, latencyComparisonChart].forEach(c => {
        if (c.options.plugins?.legend?.labels) c.options.plugins.legend.labels.color = getCSSVar("--chart-text");
        if (c.options.scales?.x) {
            c.options.scales.x.ticks.color = getCSSVar("--chart-muted");
            c.options.scales.x.grid.color = getCSSVar("--grid-color");
            c.options.scales.y.ticks.color = getCSSVar("--chart-muted");
            c.options.scales.y.grid.color = getCSSVar("--grid-color");
        }
        c.update();
    });
});

/* ───────── Telemetry Update Loop ───────── */
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
        const payload = await response.json();
        const data = payload.cache;
        const traffic = payload.traffic;
        const status = document.getElementById("status");
        const statusText = document.getElementById("statusText");

        if (!data || !data.connected) {
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
        document.getElementById("threadCount").innerText = `${data.active_threads} / ${data.total_threads}`;

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

        // Update Latency Comparison Chart
        if (latencyComparisonChart.data.labels.length >= 20) {
            latencyComparisonChart.data.labels.shift();
            latencyComparisonChart.data.datasets[0].data.shift();
            latencyComparisonChart.data.datasets[1].data.shift();
        }
        latencyComparisonChart.data.labels.push(now);
        
        // Hide/show dataset depending on simulation target mode
        if (traffic.mode === "cache") {
            latencyComparisonChart.data.datasets[0].data.push(traffic.avg_cache_lat_ms || data.avg_latency_ms);
            latencyComparisonChart.data.datasets[1].data.push(null);
        } else if (traffic.mode === "db") {
            latencyComparisonChart.data.datasets[0].data.push(null);
            latencyComparisonChart.data.datasets[1].data.push(traffic.avg_db_lat_ms);
        } else {
            latencyComparisonChart.data.datasets[0].data.push(traffic.avg_cache_lat_ms || data.avg_latency_ms);
            latencyComparisonChart.data.datasets[1].data.push(traffic.avg_db_lat_ms);
        }
        latencyComparisonChart.update();

        document.getElementById("lastUpdated").innerText = now;
    } catch (error) {
        document.getElementById("status").className = "status offline";
        document.getElementById("statusText").innerText = "CONNECTION ERROR";
    }
}
updateMetrics();
setInterval(updateMetrics, 16.66);