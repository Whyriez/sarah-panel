import os
import platform
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.system.log_manager import follow_file, simulate_app_logs

router = APIRouter(tags=["Logs"])

# Path Log Nginx (Sesuaikan nanti kalau di Linux)
LOG_DIR_LINUX = "/var/log/nginx"
# Path Log PM2 (Sesuaikan user)
PM2_LOG_DIR = os.path.expanduser("~/.pm2/logs")


@router.websocket("/ws/logs/{type}/{identifier}")
async def websocket_logs(websocket: WebSocket, type: str, identifier: str):
    """
    type: 'nginx' atau 'app'
    identifier: nama domain (misal: toko-alim.com)
    """
    await websocket.accept()

    try:
        if platform.system() == "Windows":
            # --- MODE SIMULASI WINDOWS ---
            await websocket.send_text(f"\x1b[33m[WINDOWS DEV MODE] Simulating logs for {identifier}...\x1b[0m\r\n")
            async for line in simulate_app_logs(identifier):
                await websocket.send_text(line)
        else:
            # --- MODE REAL LINUX ---
            log_path = ""
            if type == 'nginx':
                # Log Nginx Access
                log_path = f"{LOG_DIR_LINUX}/{identifier}_access.log"
            elif type == 'app':
                # Log PM2 (Out Log)
                log_path = f"{PM2_LOG_DIR}/{identifier}-out.log"

            await websocket.send_text(f"\x1b[32mStreaming logs form: {log_path}...\x1b[0m\r\n")

            # Streaming Real File
            async for line in follow_file(log_path):
                await websocket.send_text(line)

    except WebSocketDisconnect:
        print("Log Client Disconnected")
    except Exception as e:
        print(f"Log Error: {e}")
        await websocket.close()