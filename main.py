import psutil
import subprocess
import time


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


def gather_system_stats(sample_interval=1.0):
    stats = {
        "cpu": {},
        "ram": {},
        "disks": [],
        "gpus": []
    }

    # -----------------------
    # CPU (Overall Only)
    # -----------------------
    stats["cpu"]["usage_percent"] = psutil.cpu_percent(interval=sample_interval)

    # -----------------------
    # RAM
    # -----------------------
    vm = psutil.virtual_memory()
    stats["ram"] = {
        "total_mb": vm.total / (1024 ** 2),
        "used_mb": vm.used / (1024 ** 2),
        "percent_used": vm.percent
    }

    # -----------------------
    # Disk Read/Write Activity
    # -----------------------
    disk_io_1 = psutil.disk_io_counters(perdisk=True)
    time.sleep(sample_interval)
    disk_io_2 = psutil.disk_io_counters(perdisk=True)

    for disk_name in disk_io_1:
        if disk_name in disk_io_2:
            read_bytes = disk_io_2[disk_name].read_bytes - disk_io_1[disk_name].read_bytes
            write_bytes = disk_io_2[disk_name].write_bytes - disk_io_1[disk_name].write_bytes

            stats["disks"].append({
                "disk": disk_name,
                "read_MB_per_sec": read_bytes / (1024 ** 2) / sample_interval,
                "write_MB_per_sec": write_bytes / (1024 ** 2) / sample_interval
            })

    # -----------------------
    # NVIDIA GPUs
    # -----------------------
    stats["gpus"] = get_nvidia_gpus()

    return stats





if __name__ == "__main__":
    from pprint import pprint
    pprint(gather_system_stats())
