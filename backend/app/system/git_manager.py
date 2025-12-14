import os
import subprocess

def git_clone(repo_url: str, target_dir: str):
    """Clone repo pertama kali"""
    try:
        # Hapus folder target kalau sudah ada isinya (hati-hati!)
        # Untuk MVP, kita asumsikan folder masih kosong atau kita force
        if os.path.exists(target_dir) and os.listdir(target_dir):
             print(f"⚠️ Folder {target_dir} not empty, skipping clone.")
             return False, "Folder not empty"

        cmd = ["git", "clone", repo_url, target_dir]
        subprocess.run(cmd, check=True)
        return True, "Cloned successfully"
    except Exception as e:
        return False, str(e)


def git_pull(target_dir: str, branch: str = "main"):
    """Tarik update terbaru dengan memaksa fetch origin"""
    try:
        # 1. Pastikan folder itu adalah repo git
        if not os.path.exists(os.path.join(target_dir, ".git")):
            return False, "Not a git repository"

        # 2. Fetch KHUSUS branch yang diminta dari origin
        # Ini akan membuat referensi FETCH_HEAD
        print(f"🔄 Fetching origin/{branch}...")
        subprocess.run(["git", "fetch", "origin", branch], cwd=target_dir, check=True)

        # 3. Reset Hard ke branch tersebut
        # Kita pakai 'origin/branch' karena kita mau menyamakan persis dengan remote
        print(f"Testing reset to origin/{branch}...")
        subprocess.run(["git", "reset", "--hard", f"origin/{branch}"], cwd=target_dir, check=True)

        return True, "Pulled successfully"
    except subprocess.CalledProcessError as e:
        # Tangkap error outputnya
        return False, f"Git Error: {e}"
    except Exception as e:
        return False, str(e)