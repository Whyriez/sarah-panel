import os
import asyncio
import time


async def follow_file(filepath: str):
    """
    Generator Async yang meniru perilaku 'tail -f'.
    Membaca baris baru yang ditambahkan ke file.
    """
    # Cek file ada atau tidak
    if not os.path.exists(filepath):
        # Kalau log belum ada (misal app baru dibuat), kita tungguin
        yield f"Waiting for log file: {filepath}...\n"
        while not os.path.exists(filepath):
            await asyncio.sleep(1)

    # Buka file
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        # Pindah kursor ke AKHIR file (kita cuma mau baca log baru, bukan log seminggu lalu)
        f.seek(0, os.SEEK_END)

        while True:
            line = f.readline()
            if not line:
                # Kalau gak ada baris baru, tidur sebentar biar gak makan CPU
                await asyncio.sleep(0.1)
                continue

            yield line


# Helper untuk simulasi Log di Windows (Buat testing aja)
async def simulate_app_logs(domain: str):
    """
    Kalau di Windows, kita pura-pura generate log biar kelihatan jalan.
    """
    dummy_logs = [
        f"[INFO] {domain} receiving request GET /",
        f"[INFO] {domain} processing database query...",
        f"[WARN] {domain} load average is high!",
        f"[INFO] {domain} request completed in 20ms",
        f"[ERROR] {domain} connection timeout (Simulated)",
    ]
    import random
    while True:
        yield f"{time.strftime('%Y-%m-%d %H:%M:%S')} {random.choice(dummy_logs)}\n"
        await asyncio.sleep(random.uniform(0.5, 2.0))