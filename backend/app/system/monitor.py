import psutil
import platform
from datetime import datetime


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

    # 3. Disk Usage (Root path /)
    disk = psutil.disk_usage('/')
    disk_total_gb = round(disk.total / (1024 ** 3), 2)
    disk_used_gb = round(disk.used / (1024 ** 3), 2)

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
            "total_gb": disk_total_gb,
            "used_gb": disk_used_gb,
            "percent": disk.percent
        },
        "system": {
            "os": os_info,
            "boot_time": boot_time
        }
    }
