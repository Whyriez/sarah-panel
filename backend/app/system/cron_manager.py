from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import subprocess
import logging
from datetime import datetime

# Setup Logger
logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.ERROR)

scheduler = BackgroundScheduler()


def run_shell_command(command, job_id):
    """Fungsi yang dieksekusi saat jadwal tiba"""
    print(f"⏰ [CRON] Executing Job #{job_id}: {command}")
    try:
        # Jalankan command (Simulasi atau Real)
        # Di Windows kita print aja biar aman, atau run subprocess
        subprocess.run(command, shell=True, check=True)
        print(f"✅ [CRON] Job #{job_id} Success")
    except Exception as e:
        print(f"❌ [CRON] Job #{job_id} Failed: {e}")


# Fungsi untuk Refresh Jadwal dari Database (Dipanggil saat start atau ada update)
def reload_jobs_from_db(db_session):
    from app.modules.cron.models import CronJob

    # 1. Hapus semua job lama di memori (biar gak duplikat)
    scheduler.remove_all_jobs()

    # 2. Ambil dari DB
    jobs = db_session.query(CronJob).filter(CronJob.is_active == True).all()

    # 3. Masukkan ke Scheduler
    for job in jobs:
        try:
            # Parse format cron string "min hour day month dow" -> CronTrigger
            # Contoh simple: "* * * * *"
            # Agar tidak ribet parsing string cron manual, kita pakai interval simple dulu untuk MVP
            # Atau kita paksa user input format 5 bintang standar Linux

            # Kita pecah string "m h d M w"
            parts = job.schedule.split(" ")
            if len(parts) != 5:
                print(f"⚠️ Invalid Schedule Format Job #{job.id}: {job.schedule}")
                continue

            trigger = CronTrigger(
                minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4]
            )

            scheduler.add_job(
                run_shell_command,
                trigger,
                args=[job.command, job.id],
                id=str(job.id),
                replace_existing=True
            )
            print(f"📅 Loaded Cron Job: {job.name} ({job.schedule})")

        except Exception as e:
            print(f"⚠️ Failed to load job #{job.id}: {e}")


def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        print("⏰ Cron Scheduler Started!")