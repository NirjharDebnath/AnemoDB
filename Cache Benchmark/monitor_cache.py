import socket
import time
import os
import datetime
import subprocess


CACHE_HOST = "127.0.0.1"
CACHE_PORT = 8080
REFRESH_INTERVAL = 4


# Terminal colors
BLUE = "\033[1;34m"
CYAN = "\033[1;36m"
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
RED = "\033[1;31m"
GRAY = "\033[0;37m"
RESET = "\033[0m"


def fetch_stats():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect((CACHE_HOST, CACHE_PORT))

            payload = "STATS\n<EOQ>\n"
            s.sendall(payload.encode("utf-8"))

            raw_res = b""

            while b"<EOQ>" not in raw_res:
                chunk = s.recv(1024)

                if not chunk:
                    break

                raw_res += chunk

            res = raw_res.decode("utf-8", errors="replace")

            return res.replace("<EOQ>", "").strip()

    except Exception as e:
        return (
            f"{RED}[!] Anemo server unavailable{RESET}\n"
            f"    Target : {CACHE_HOST}:{CACHE_PORT}\n"
            f"    Error  : {e}"
        )


def clear_screen():
    subprocess.run(
        "cls" if os.name == "nt" else "clear",
        shell=True
    )


def print_dashboard(stats_output):

    timestamp = datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    print(
        BLUE
        + "╔══════════════════════════════════════════════════════╗"
        + RESET
    )

    print(
        BLUE
        + "║"
        + RESET
        + "               "
        + CYAN
        + "LIVE ANEMO_DB DASHBOARD "
        + RESET
        + "               "
        + BLUE
        + "║"
        + RESET
    )

    print(
        BLUE
        + "╠══════════════════════════════════════════════════════╣"
        + RESET
    )

    print(
        "║  "
        + f"{GRAY}Last Updated{RESET}"
        + " : "
        + timestamp.ljust(36)
        + " ║"
    )

    print(
        "║  "
        + f"{GRAY}Target      {RESET}"
        + " : "
        + f"{GREEN}{CACHE_HOST}:{CACHE_PORT}{RESET}".ljust(45)
        + "   ║"
    )

    print(
        BLUE
        + "╚══════════════════════════════════════════════════════╝"
        + RESET
    )

    print()

    print(stats_output)

    print()
    print(
        GRAY
        + f"  Refreshing every {REFRESH_INTERVAL} seconds..."
        + RESET
    )


if __name__ == "__main__":

    while True:

        stats_output = fetch_stats()
        clear_screen()
        print_dashboard(stats_output)
        time.sleep(REFRESH_INTERVAL)