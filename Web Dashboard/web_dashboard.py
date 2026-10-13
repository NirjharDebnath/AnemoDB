import os
import socket
import json
from flask import Flask, render_template, jsonify, request
from traffic_generator import generator

app = Flask(__name__)

ANEMO_HOST = os.environ.get("ANEMO_HOST", "127.0.0.1")
ANEMO_PORT = int(os.environ.get("ANEMO_PORT", "8080"))

def fetch_stats_from_cpp():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect((ANEMO_HOST, ANEMO_PORT))
            s.sendall(b"STATS_JSON\n<EOQ>\n")

            raw_res = b""
            while b"<EOQ>" not in raw_res:
                chunk = s.recv(2048)
                if not chunk:
                    break
                raw_res += chunk

            text = raw_res.decode("utf-8", errors="replace").replace("<EOQ>", "").strip()
            data = json.loads(text)
            data["connected"] = True
            return data
    except Exception as e:
        return {
            "error": str(e),
            "connected": False,
            "requests": 0,
            "hits": 0,
            "misses": 0,
            "hit_rate": 0.0,
            "throughput": 0.0,
            "avg_latency_ms": 0.0,
            "uptime_sec": 0,
            "cache_lines": 0,
            "max_capacity": 0,
            "kb": 0.0,
            "queue_length": 0,
            "active_threads": 0,
            "total_threads": 0,
            "directory_size": 0
        }

@app.route("/")
def home():
    return render_template("index.html", host=ANEMO_HOST, port=ANEMO_PORT)

@app.route("/api/stats")
def get_stats():
    cpp_stats = fetch_stats_from_cpp()
    traffic_stats = generator.get_metrics()
    return jsonify({
        "cache": cpp_stats,
        "traffic": traffic_stats
    })

@app.route("/api/traffic/control", methods=["POST"])
def control_traffic():
    body = request.get_json() or {}
    running = body.get("running", False)
    mode = body.get("mode", "both")
    threads = int(body.get("threads", 4))
    generator.set_config(running, mode, threads)
    return jsonify(generator.get_metrics())

if __name__ == "__main__":
    bind_host = os.environ.get("DASHBOARD_HOST", "0.0.0.0")
    bind_port = int(os.environ.get("DASHBOARD_PORT", "5000"))
    print(f">>> AnemoDB Telemetry Dashboard running at http://127.0.0.1:{bind_port}")
    app.run(host=bind_host, port=bind_port, debug=False)