import psutil
import subprocess
import time
import sqlite3
from datetime import datetime

# ==========================
# CONFIG
# ==========================
SAMPLE_INTERVAL = 60  # seconds
DB_NAME = "system_monitor.db"


# ==========================
# GPU FUNCTION
# ==========================
def get_nvidia_gpus():
    gpus = []

    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits"
            ],
            capture_output=True,
            text=True,
            check=True
        )

        lines = result.stdout.strip().split("\n")

        for i, line in enumerate(lines):
            name, temp_c, util, mem_used, mem_total = [x.strip() for x in line.split(",")]

            temp_c = float(temp_c)
            temp_f = (temp_c * 9/5) + 32

            mem_used = float(mem_used)
            mem_total = float(mem_total)

            gpus.append({
                "index": i,
                "name": name,
                "temperature_c": temp_c,
                "temperature_f": temp_f,
                "usage_percent": float(util),
                "memory_used_mb": mem_used,
                "memory_total_mb": mem_total,
                "memory_usage_percent": (mem_used / mem_total) * 100 if mem_total > 0 else 0
            })

    except Exception as e:
        gpus.append({"error": str(e)})

    return gpus


# ==========================
# DATABASE SETUP
# ==========================
def initialize_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cpu (
            timestamp TEXT PRIMARY KEY,
            usage_percent REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ram (
            timestamp TEXT PRIMARY KEY,
            total_mb REAL,
            used_mb REAL,
            percent_used REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS disk (
            timestamp TEXT,
            disk_name TEXT,
            read_mb_per_sec REAL,
            write_mb_per_sec REAL,
            PRIMARY KEY (timestamp, disk_name)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gpu (
            timestamp TEXT,
            gpu_index INTEGER,
            name TEXT,
            temperature_c REAL,
            temperature_f REAL,
            usage_percent REAL,
            memory_used_mb REAL,
            memory_total_mb REAL,
            memory_usage_percent REAL,
            PRIMARY KEY (timestamp, gpu_index)
        )
    """)

    conn.commit()
    conn.close()


# ==========================
# DATA COLLECTION
# ==========================
def collect_and_store():
    timestamp = datetime.utcnow().isoformat()

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # ---- CPU ----
    cpu_usage = psutil.cpu_percent(interval=1)
    cursor.execute(
        "INSERT INTO cpu VALUES (?, ?)",
        (timestamp, cpu_usage)
    )

    # ---- RAM ----
    vm = psutil.virtual_memory()
    cursor.execute(
        "INSERT INTO ram VALUES (?, ?, ?, ?)",
        (timestamp, vm.total / (1024 ** 2), vm.used / (1024 ** 2), vm.percent)
    )

    # ---- Disk ----
    disk_io_1 = psutil.disk_io_counters(perdisk=True)
    time.sleep(1)
    disk_io_2 = psutil.disk_io_counters(perdisk=True)

    for disk_name in disk_io_1:
        if disk_name in disk_io_2:
            read_bytes = disk_io_2[disk_name].read_bytes - disk_io_1[disk_name].read_bytes
            write_bytes = disk_io_2[disk_name].write_bytes - disk_io_1[disk_name].write_bytes

            cursor.execute(
                "INSERT INTO disk VALUES (?, ?, ?, ?)",
                (
                    timestamp,
                    disk_name,
                    read_bytes / (1024 ** 2),
                    write_bytes / (1024 ** 2)
                )
            )

    # ---- GPU ----
    gpus = get_nvidia_gpus()
    for gpu in gpus:
        if "error" not in gpu:
            cursor.execute(
                "INSERT INTO gpu VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    timestamp,
                    gpu["index"],
                    gpu["name"],
                    gpu["temperature_c"],
                    gpu["temperature_f"],
                    gpu["usage_percent"],
                    gpu["memory_used_mb"],
                    gpu["memory_total_mb"],
                    gpu["memory_usage_percent"]
                )
            )

    conn.commit()
    conn.close()


# ==========================
# MAIN LOOP
# ==========================
if __name__ == "__main__":
    initialize_database()
    print("Monitoring started...")

    while True:
        collect_and_store()
        time.sleep(SAMPLE_INTERVAL)
