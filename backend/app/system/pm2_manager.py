import subprocess
import platform
import os

# Deteksi apakah kita di Windows (Dev) atau Linux (Prod)
IS_WINDOWS = platform.system() == "Windows"


def run_command(command: list):
    """
    Menjalankan perintah terminal.
    Jika di Windows, kita cuma print (Simulasi).
    Jika di Linux, kita eksekusi beneran.
    """
    cmd_str = " ".join(command)

    if IS_WINDOWS:
        print(f"🖥️ [SIMULASI WINDOWS] Executing: {cmd_str}")
        return True, "Simulated Success"

    try:
        # Eksekusi command di Linux
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ PM2 Error: {e.stderr}")
        return False, e.stderr


def start_app(domain: str, port: int, script_path: str, interpreter: str = "node"):
    """
    Menjalankan aplikasi user menggunakan PM2.
    Command asli: pm2 start app.js --name domain.com -- --port 3000
    """

    # Kalau file script belum ada (karena user belum upload), kita buat dummy file dulu
    # biar PM2 gak error saat dicoba start
    if IS_WINDOWS and not os.path.exists(script_path):
        with open(script_path, 'w') as f:
            f.write("console.log('Hello AlimPanel');")

    app_name = domain

    # Command PM2
    # --time: log waktu
    # --name: nama process di PM2
    command = [
        "pm2", "start", script_path,
        "--name", app_name,
        "--time"
    ]

    # Inject Port via Environment Variable (Cara standar Node/Python baca port)
    # Di Linux commandnya jadi: PORT=3000 pm2 start ...
    # Tapi lewat subprocess kita set env parameter

    # Khusus simulasi, kita return sukses aja
    if IS_WINDOWS:
        return run_command(command)

    env = os.environ.copy()
    env["PORT"] = str(port)

    try:
        subprocess.run(command, env=env, check=True)

        # [FIX] SIMPAN STATE PM2 AGAR AUTO-START SETELAH REBOOT
        subprocess.run(["pm2", "save"], check=False)

        return True, "App started"
    except Exception as e:
        return False, str(e)


def delete_app(domain: str):
    success, msg = run_command(["pm2", "delete", domain])
    # [FIX] Simpan perubahan saat delete juga
    if not IS_WINDOWS:
        subprocess.run(["pm2", "save"], check=False)
    return success, msg


def reload_app(domain: str):
    return run_command(["pm2", "reload", domain])