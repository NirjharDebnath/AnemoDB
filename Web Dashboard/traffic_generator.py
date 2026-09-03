import socket
import time
import random
import threading
import psycopg2
from psycopg2 import pool
from collections import deque

CACHE_HOST = '127.0.0.1'
CACHE_PORT = 8080

DB_CONFIG = {
    "dbname": "college_db",
    "user": "postgres",
    "password": "postgres",
    "host": "127.0.0.1",
    "port": 5432
}

QUERY_TEMPLATES = [
    ("EASY", "SELECT student_id, roll_number, name FROM students WHERE student_id = {};"),
    ("EASY", "SELECT * FROM faculty WHERE department_id = {};"),
    ("MEDIUM", "SELECT s.name, c.course_name, m.marks, m.grade FROM students s JOIN marks m ON s.student_id = m.student_id JOIN courses c ON m.course_id = c.course_id WHERE s.student_id = {};"),
    ("MEDIUM", "SELECT c.course_name, f.name FROM courses c JOIN faculty f ON c.department_id = f.department_id WHERE c.course_id = {};"),
    ("COMPLEX", "SELECT d.department_name, AVG(m.marks) AS avg_score FROM departments d JOIN students s ON d.department_id = s.department_id JOIN marks m ON s.student_id = m.student_id GROUP BY d.department_name;"),
    ("COMPLEX", "SELECT course_id, COUNT(student_id) as enrolled_count FROM enrollments GROUP BY course_id ORDER BY enrolled_count DESC LIMIT 5;")
]

class TrafficGenerator:
    def __init__(self):
        self.running = False
        self.mode = "cache"  # 'cache', 'db', or 'both'
        self.target_threads = 4
        self.active_threads = 0
        self.lock = threading.Lock()
        
        self.cache_latencies = deque(maxlen=100)
        self.db_latencies = deque(maxlen=100)
        self.cache_req_count = 0
        self.db_req_count = 0
        
        self.db_pool = None
        self._init_db_pool()

    def _init_db_pool(self):
        try:
            self.db_pool = psycopg2.pool.ThreadedConnectionPool(minconn=1, maxconn=50, **DB_CONFIG)
        except Exception as e:
            print(f"[TrafficGen] DB Pool Init Error: {e}")

    def generate_query(self):
        q_type, q_template = random.choice(QUERY_TEMPLATES)
        if "student_id =" in q_template:
            query = q_template.format(random.randint(1, 100))
        elif "department_id =" in q_template:
            query = q_template.format(random.randint(1, 6))
        elif "course_id =" in q_template:
            query = q_template.format(random.randint(1, 120))
        else:
            query = q_template
        return query

    def query_cache(self, query):
        start = time.perf_counter()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3.0)
                s.connect((CACHE_HOST, CACHE_PORT))
                s.sendall((query + "\n<EOQ>\n").encode('utf-8'))
                res = b""
                while b"<EOQ>" not in res:
                    chunk = s.recv(1024)
                    if not chunk: break
                    res += chunk
        except Exception:
            pass
        return (time.perf_counter() - start) * 1000.0

    def query_db(self, query):
        start = time.perf_counter()
        conn = None
        try:
            if not self.db_pool:
                self._init_db_pool()
            conn = self.db_pool.getconn()
            cur = conn.cursor()
            cur.execute(query)
            cur.fetchall()
            cur.close()
        except Exception:
            pass
        finally:
            if conn and self.db_pool:
                self.db_pool.putconn(conn)
        return (time.perf_counter() - start) * 1000.0

    def worker_loop(self):
        while True:
            with self.lock:
                if not self.running or self.active_threads > self.target_threads:
                    self.active_threads -= 1
                    break

            query = self.generate_query()

            if self.mode in ("cache", "both"):
                lat = self.query_cache(query)
                with self.lock:
                    self.cache_latencies.append(lat)
                    self.cache_req_count += 1

            if self.mode in ("db", "both"):
                lat = self.query_db(query)
                with self.lock:
                    self.db_latencies.append(lat)
                    self.db_req_count += 1

            time.sleep(0.01)

    def set_config(self, running: bool, mode: str, threads: int):
        with self.lock:
            self.running = running
            self.mode = mode
            self.target_threads = max(1, min(threads, 32))

            if self.running:
                needed = self.target_threads - self.active_threads
                for _ in range(needed):
                    self.active_threads += 1
                    t = threading.Thread(target=self.worker_loop, daemon=True)
                    t.start()

    def get_metrics(self):
        with self.lock:
            avg_cache = sum(self.cache_latencies) / len(self.cache_latencies) if self.cache_latencies else 0.0
            avg_db = sum(self.db_latencies) / len(self.db_latencies) if self.db_latencies else 0.0
            return {
                "running": self.running,
                "mode": self.mode,
                "threads": self.active_threads,
                "avg_cache_lat_ms": round(avg_cache, 2),
                "avg_db_lat_ms": round(avg_db, 2),
                "cache_requests": self.cache_req_count,
                "db_requests": self.db_req_count
            }

generator = TrafficGenerator()
