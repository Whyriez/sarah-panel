import psutil
import platform
from datetime import datetime
import shutil

def get_system_stats():
    """
    Mengambil data real-time CPU, RAM, Disk, dan Info OS.
    """
    # 1. CPU Usage (Interval 0.1s biar gak blocking lama)
    cpu_percent = psutil.cpu_percent(interval=0.1)

    # 2. RAM Usage
    memory = psutil.virtual_memory()
    ram_total_gb = round(memory.total / (1024 ** 3), 2)
    ram_used_gb = round(memory.used / (1024 ** 3), 2)

    # Disk Usage
    total, used, free = shutil.disk_usage("/")
    disk_percent = (used / total) * 100

    # 4. Boot Time & OS
    boot_time = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
    os_info = f"{platform.system()} {platform.release()}"

    return {
        "cpu": {
            "usage_percent": cpu_percent,
            "cores": psutil.cpu_count()
        },
        "memory": {
            "total_gb": ram_total_gb,
            "used_gb": ram_used_gb,
            "percent": memory.percent
        },
        "disk": {
            "total_gb": total // (2**30),
            "used_gb": used // (2**30),
            "free_gb": free // (2**30),
            "percent": round(disk_percent, 1)
        },
        "system": {
            "os": os_info,
            "boot_time": boot_time
        }
    }
