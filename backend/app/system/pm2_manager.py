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


def start_app(domain: str, port: int, cwd: str, command: str = None):
    try:
        # Stop dulu kalau ada
        subprocess.run(["pm2", "delete", domain], check=False, capture_output=True)

        # Default Command Logic
        if not command:
            if os.path.exists(os.path.join(cwd, "package.json")):
                command = "npm start"
            elif os.path.exists(os.path.join(cwd, "app.py")):
                command = "python3 app.py"
            else:
                command = "node index.js"

        print(f"🚀 Starting {domain} with command: {command}")

        # PM2 Start Command
        # Kita gunakan 'pm2 start "cmd" --name domain'
        cmd = [
            "pm2", "start", command,
            "--name", domain,
            "--cwd", cwd,
            "--time"  # Menampilkan timestamp di log
        ]

        subprocess.run(cmd, check=True)
        subprocess.run(["pm2", "save"], check=True)

        return True, "Started"
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