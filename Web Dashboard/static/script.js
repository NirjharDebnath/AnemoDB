function getCSSVar(name) {
    return getComputedStyle(document.body).getPropertyValue(name).trim();
}

/* ───────── Chart Initializations ───────── */
const hitMissChart = new Chart(document.getElementById("hitMissChart").getContext("2d"), {
    type: "doughnut",
    data: {
        labels: ["Cache Hits", "Cache Misses"],
        datasets: [{
            data: [0, 0],
            backgroundColor: ["#39d98a", "#ff5c70"],
            borderWidth: 0,
            hoverOffset: 6
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "72%",
        plugins: {
            legend: {
                position: "bottom",
                labels: {
                    color: getCSSVar("--chart-text"),
                    padding: 16,
                    usePointStyle: true
                }
            }
        }
    }
});

const throughputChart = new Chart(document.getElementById("throughputChart").getContext("2d"), {
    type: "line",
    data: {
        labels: [],
        datasets: [{
            label: "Requests / sec",
            data: [],
            borderColor: "#00e5ff",
            backgroundColor: "rgba(0, 229, 255, 0.08)",
            fill: true,
            tension: 0.35,
            pointRadius: 2,
            pointHoverRadius: 5
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        scales: {
            x: { ticks: { color: getCSSVar("--chart-muted"), maxTicksLimit: 8 }, grid: { color: getCSSVar("--grid-color") } },
            y: { beginAtZero: true, ticks: { color: getCSSVar("--chart-muted") }, grid: { color: getCSSVar("--grid-color") } }
        },
        plugins: {
            legend: { labels: { color: getCSSVar("--chart-text") } }
        }
    }
});

const latencyComparisonChart = new Chart(document.getElementById("latencyComparisonChart").getContext("2d"), {
    type: "line",
    data: {
        labels: [],
        datasets: [
            {
                label: "Cache Latency (ms)",
                data: [],
                borderColor: "#39d98a",
                backgroundColor: "rgba(57, 217, 138, 0.08)",
                fill: false,
                tension: 0.3,
                pointRadius: 2
            },
            {
                label: "PostgreSQL Latency (ms)",
                data: [],
                borderColor: "#ff5c70",
                backgroundColor: "rgba(255, 92, 112, 0.08)",
                fill: false,
                tension: 0.3,
                pointRadius: 2
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        scales: {
            x: { ticks: { color: getCSSVar("--chart-muted"), maxTicksLimit: 8 }, grid: { color: getCSSVar("--grid-color") } },
            y: { beginAtZero: true, ticks: { color: getCSSVar("--chart-muted") }, grid: { color: getCSSVar("--grid-color") } }
        },
        plugins: {
            legend: { labels: { color: getCSSVar("--chart-text") } }
        }
    }
});

/* ───────── Simulation Controls ───────── */
let isSimulating = false;
const simToggleBtn = document.getElementById("simToggleBtn");
const simTarget = document.getElementById("simTarget");
const threadSlider = document.getElementById("threadSlider");
const threadVal = document.getElementById("threadVal");

threadSlider.addEventListener("input", (e) => {
    threadVal.innerText = `${e.target.value} clients`;
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
        simToggleBtn.style.borderColor = isSimulating ? "var(--red)" : "var(--blue)";
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
    if (minutes < 60) return minutes + "m " + (seconds % 60) + "s";
    const hours = Math.floor(minutes / 60);
    return hours + "h " + (minutes % 60) + "m";
}

async function updateMetrics() {
    try {
        const response = await fetch("/api/stats");
        const payload = await response.json();
        const data = payload.cache || {};
        const traffic = payload.traffic || {};

        const status = document.getElementById("status");
        const statusText = document.getElementById("statusText");
        const pgStatus = document.getElementById("pgStatus");
        const pgStatusText = document.getElementById("pgStatusText");
        const speedupBadge = document.getElementById("speedupBadge");
        const activeQuery = document.getElementById("activeQuery");

        // 1. Update Anemo Cache Status Dot
        if (data && data.connected) {
            status.className = "status online";
            statusText.innerText = "Cache: ONLINE";
        } else {
            status.className = "status offline";
            statusText.innerText = "Cache: OFFLINE";
        }

        // 2. Update PostgreSQL Status Dot
        if (traffic && traffic.db_connected) {
            pgStatus.className = "status online";
            pgStatusText.innerText = "DB: ONLINE";
        } else {
            pgStatus.className = "status offline";
            pgStatusText.innerText = "DB: OFFLINE";
        }

        // 3. Update Active Query Ticker
        if (traffic.last_query) {
            activeQuery.innerText = traffic.last_query;
        }

        // 4. Update Speedup Badge
        if (traffic.running && traffic.speedup > 0) {
            speedupBadge.className = "badge-speedup active";
            speedupBadge.innerText = `${traffic.speedup}x Faster`;
        } else if (traffic.running) {
            speedupBadge.className = "badge-speedup";
            speedupBadge.innerText = "Measuring...";
        } else {
            speedupBadge.className = "badge-speedup";
            speedupBadge.innerText = "Idle (Start Load)";
        }

        // 5. Update Metrics Grid
        if (data && data.connected) {
            document.getElementById("hitRate").innerText = (data.hit_rate || 0).toFixed(1) + "%";
            document.getElementById("throughput").innerText = (data.throughput || 0).toFixed(2);
            document.getElementById("avgLatency").innerText = (data.avg_latency_ms || 0).toFixed(2) + " ms";
            document.getElementById("uptime").innerText = formatUptime(data.uptime_sec || 0);
            document.getElementById("slotUsage").innerText = `${data.cache_lines || 0} / ${data.max_capacity || 0}`;
            document.getElementById("memUsage").innerText = (data.kb || 0).toFixed(2) + " KB";
            document.getElementById("totalRequests").innerText = (data.requests || 0).toLocaleString();
            document.getElementById("queue").innerText = data.queue_length || 0;
            document.getElementById("hits").innerText = (data.hits || 0).toLocaleString();
            document.getElementById("misses").innerText = (data.misses || 0).toLocaleString();
            document.getElementById("directory").innerText = data.directory_size || 0;
            document.getElementById("threadCount").innerText = `${data.active_threads || 0} / ${data.total_threads || 0}`;

            const utilization = data.max_capacity > 0 ? (data.cache_lines / data.max_capacity) * 100 : 0;
            document.getElementById("utilBar").style.width = Math.min(utilization, 100) + "%";
            document.getElementById("utilText").innerText = utilization.toFixed(1) + "%";

            hitMissChart.data.datasets[0].data = [data.hits || 0, data.misses || 0];
            hitMissChart.update();
        }

        document.getElementById("trafficReqCount").innerText = (traffic.cache_requests || 0) + (traffic.db_requests || 0);

        // 6. Update Throughput Trend Chart
        const now = new Date().toLocaleTimeString();
        if (throughputChart.data.labels.length >= 25) {
            throughputChart.data.labels.shift();
            throughputChart.data.datasets[0].data.shift();
        }
        throughputChart.data.labels.push(now);
        throughputChart.data.datasets[0].data.push(data.connected ? (data.throughput || 0) : 0);
        throughputChart.update();

        // 7. Update Latency Comparison Chart
        if (latencyComparisonChart.data.labels.length >= 25) {
            latencyComparisonChart.data.labels.shift();
            latencyComparisonChart.data.datasets[0].data.shift();
            latencyComparisonChart.data.datasets[1].data.shift();
        }
        latencyComparisonChart.data.labels.push(now);

        if (traffic.running) {
            const cacheLat = traffic.avg_cache_lat_ms > 0 ? traffic.avg_cache_lat_ms : (data.avg_latency_ms || null);
            const dbLat = traffic.avg_db_lat_ms > 0 ? traffic.avg_db_lat_ms : null;

            if (traffic.mode === "cache") {
                latencyComparisonChart.data.datasets[0].data.push(cacheLat);
                latencyComparisonChart.data.datasets[1].data.push(null);
            } else if (traffic.mode === "db") {
                latencyComparisonChart.data.datasets[0].data.push(null);
                latencyComparisonChart.data.datasets[1].data.push(dbLat);
            } else {
                latencyComparisonChart.data.datasets[0].data.push(cacheLat);
                latencyComparisonChart.data.datasets[1].data.push(dbLat);
            }
        } else {
            // Idle state: record live cache latency if available, null for db
            latencyComparisonChart.data.datasets[0].data.push(data.connected ? (data.avg_latency_ms || 0) : null);
            latencyComparisonChart.data.datasets[1].data.push(null);
        }
        latencyComparisonChart.update();

        document.getElementById("lastUpdated").innerText = now;
    } catch (error) {
        document.getElementById("status").className = "status offline";
        document.getElementById("statusText").innerText = "Cache: DISCONNECTED";
    }
}

// Initial fetch and 1-second interval
updateMetrics();
setInterval(updateMetrics, 1000);