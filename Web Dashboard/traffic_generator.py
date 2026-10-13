import os
import socket
import time
import random
import threading
from collections import deque

try:
    import psycopg2
    from psycopg2 import pool
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

CACHE_HOST = os.environ.get("ANEMO_HOST", "127.0.0.1")
CACHE_PORT = int(os.environ.get("ANEMO_PORT", "8080"))

DB_CONFIG = {
    "dbname": os.environ.get("PGDATABASE", "college_db"),
    "user": os.environ.get("PGUSER", "postgres"),
    "password": os.environ.get("PGPASSWORD", "postgres"),
    "host": os.environ.get("PGHOST", "127.0.0.1"),
    "port": int(os.environ.get("PGPORT", "5432"))
}

QUERY_TEMPLATES = [
    ("POINT_LOOKUP", "SELECT student_id, roll_number, name FROM students WHERE student_id = {};"),
    ("INDEXED_FILTER", "SELECT * FROM faculty WHERE department_id = {};"),
    ("RELATIONAL_JOIN", "SELECT s.name, c.course_name, m.marks, m.grade FROM students s JOIN marks m ON s.student_id = m.student_id JOIN courses c ON m.course_id = c.course_id WHERE s.student_id = {};"),
    ("FACULTY_JOIN", "SELECT c.course_name, f.name FROM courses c JOIN faculty f ON c.department_id = f.department_id WHERE c.course_id = {};"),
    ("AGGREGATION", "SELECT d.department_name, AVG(m.marks) AS avg_score FROM departments d JOIN students s ON d.department_id = s.department_id JOIN marks m ON s.student_id = m.student_id GROUP BY d.department_name;"),
    ("TOP_K_SORT", "SELECT course_id, COUNT(student_id) as enrolled_count FROM enrollments GROUP BY course_id ORDER BY enrolled_count DESC LIMIT 5;")
]

class TrafficGenerator:
    def __init__(self):
        self.running = False
        self.mode = "both"  # 'cache', 'db', or 'both'
        self.target_threads = 4
        self.active_threads = 0
        self.lock = threading.Lock()
        
        self.cache_latencies = deque(maxlen=120)
        self.db_latencies = deque(maxlen=120)
        self.cache_req_count = 0
        self.db_req_count = 0
        self.last_query = "SELECT student_id, name FROM students WHERE student_id = 42;"
        
        self.db_pool = None
        self.db_connected = False
        self.cache_connected = False
        self._init_db_pool()

    def _init_db_pool(self):
        if not HAS_PSYCOPG2:
            self.db_connected = False
            return
        try:
            self.db_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=40,
                connect_timeout=3,
                **DB_CONFIG
            )
            # Health check 1 connection
            conn = self.db_pool.getconn()
            self.db_pool.putconn(conn)
            self.db_connected = True
        except Exception as e:
            self.db_pool = None
            self.db_connected = False

    def generate_query(self):
        _, q_template = random.choice(QUERY_TEMPLATES)
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
        success = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.5)
                s.connect((CACHE_HOST, CACHE_PORT))
                s.sendall((query + "\n<EOQ>\n").encode('utf-8'))
                res = b""
                while b"<EOQ>" not in res:
                    chunk = s.recv(2048)
                    if not chunk:
                        break
                    res += chunk
                if b"<EOQ>" in res:
                    success = True
                    self.cache_connected = True
        except Exception:
            self.cache_connected = False
            return None

        if not success:
            return None
        return (time.perf_counter() - start) * 1000.0

    def query_db(self, query):
        if not HAS_PSYCOPG2:
            return None
        start = time.perf_counter()
        conn = None
        success = False
        try:
            if not self.db_pool:
                self._init_db_pool()
            if not self.db_pool:
                return None
            conn = self.db_pool.getconn()
            with conn.cursor() as cur:
                cur.execute(query)
                cur.fetchall()
            success = True
            self.db_connected = True
        except Exception:
            self.db_connected = False
            return None
        finally:
            if conn and self.db_pool:
                try:
                    self.db_pool.putconn(conn)
                except Exception:
                    pass

        if not success:
            return None
        return (time.perf_counter() - start) * 1000.0

    def worker_loop(self):
        while True:
            with self.lock:
                if not self.running or self.active_threads > self.target_threads:
                    self.active_threads = max(0, self.active_threads - 1)
                    break

            query = self.generate_query()
            with self.lock:
                self.last_query = query

            if self.mode in ("cache", "both"):
                lat = self.query_cache(query)
                if lat is not None:
                    with self.lock:
                        self.cache_latencies.append(lat)
                        self.cache_req_count += 1

            if self.mode in ("db", "both"):
                lat = self.query_db(query)
                if lat is not None:
                    with self.lock:
                        self.db_latencies.append(lat)
                        self.db_req_count += 1

            # Controlled inter-query delay
            time.sleep(0.012)

    def set_config(self, running: bool, mode: str, threads: int):
        with self.lock:
            self.running = running
            self.mode = mode
            self.target_threads = max(1, min(threads, 32))

            if self.running:
                needed = self.target_threads - self.active_threads
                for _ in range(max(0, needed)):
                    self.active_threads += 1
                    t = threading.Thread(target=self.worker_loop, daemon=True)
                    t.start()

    def get_metrics(self):
        with self.lock:
            avg_cache = (sum(self.cache_latencies) / len(self.cache_latencies)) if self.cache_latencies else 0.0
            avg_db = (sum(self.db_latencies) / len(self.db_latencies)) if self.db_latencies else 0.0
            
            speedup = 0.0
            if avg_cache > 0.001 and avg_db > 0.001:
                speedup = round(avg_db / avg_cache, 1)

            return {
                "running": self.running,
                "mode": self.mode,
                "threads": self.active_threads,
                "target_threads": self.target_threads,
                "avg_cache_lat_ms": round(avg_cache, 2),
                "avg_db_lat_ms": round(avg_db, 2),
                "speedup": speedup,
                "cache_requests": self.cache_req_count,
                "db_requests": self.db_req_count,
                "db_connected": self.db_connected,
                "cache_connected": self.cache_connected,
                "last_query": self.last_query
            }

generator = TrafficGenerator()
