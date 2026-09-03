import socket
import json
from flask import Flask, render_template, jsonify, request
from traffic_generator import generator

app = Flask(__name__)

ANEMO_HOST = "127.0.0.1"
ANEMO_PORT = 8080

def fetch_stats_from_cpp():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(200)
            s.connect((ANEMO_HOST, ANEMO_PORT))
            s.sendall(b"STATS_JSON\n<EOQ>\n")

            raw_res = b""
            while b"<EOQ>" not in raw_res:
                chunk = s.recv(1024)
                if not chunk: break
                raw_res += chunk

            text = raw_res.decode("utf-8", errors="replace").replace("<EOQ>", "").strip()
            data = json.loads(text)
            data["connected"] = True
            return data
    except Exception as e:
        return {"error": str(e), "connected": False}

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
    mode = body.get("mode", "cache")
    threads = int(body.get("threads", 4))
    generator.set_config(running, mode, threads)
    return jsonify(generator.get_metrics())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)