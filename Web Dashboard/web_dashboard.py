import socket
import json
from flask import Flask, render_template, jsonify

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


@app.route("/")
def home():
    return render_template("index.html", host=ANEMO_HOST, port=ANEMO_PORT)

@app.route("/api/stats")
def get_stats():
    return jsonify(fetch_stats_from_cpp())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)