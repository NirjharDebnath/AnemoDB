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
