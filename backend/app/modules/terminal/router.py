from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.system.terminal_manager import TerminalManager
from app.core.security import SECRET_KEY, ALGORITHM
from jose import jwt
import json
import os
from app.core.database import SessionLocal
from app.modules.sites.models import Site

router = APIRouter(tags=["Terminal"])

manager = TerminalManager()
SITES_BASE_DIR = "/var/www/sarahpanel"


async def get_token_from_ws(websocket: WebSocket):
    token = websocket.query_params.get("token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except:
        return None


@router.websocket("/ws/terminal")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # 1. Auth Check
    user = await get_token_from_ws(websocket)
    if not user:
        await websocket.send_text("Error: Unauthorized\r\n")
        await websocket.close()
        return

    # 2. Cek apakah ada parameter site_id?
    site_id = websocket.query_params.get("site_id")
    target_cwd = None

    if site_id:
        # Cari folder website di DB
        db = SessionLocal()
        try:
            site = db.query(Site).filter(Site.id == site_id).first()
            if site:
                target_cwd = os.path.join(SITES_BASE_DIR, site.domain)
        finally:
            db.close()

    reader_task = None
    terminal_proc = None

    try:
        # 3. Handshake Ukuran
        initial_msg = await websocket.receive_text()
        initial_config = json.loads(initial_msg)

        cols = 80
        rows = 24
        if initial_config.get('type') == 'resize':
            cols = initial_config['cols']
            rows = initial_config['rows']

        # 4. Spawn Terminal di Folder Website!
        terminal_proc = manager.spawn_terminal(cwd=target_cwd)

        # 5. Resize & Clear
        manager.resize_terminal(terminal_proc, cols, rows)
        await manager.write_stream(terminal_proc, "cls\r" if manager.os_type == "windows" else "clear\r")

        # 6. Welcome Message
        import asyncio
        await asyncio.sleep(0.1)

        path_msg = f"📂 Working Dir: {target_cwd}" if target_cwd else "🏠 Home Directory"
        await websocket.send_text(f"\x1b[32m✅ Connected to AlimPanel Shell...\r\n{path_msg}\x1b[0m\r\n")

        reader_task = asyncio.create_task(manager.read_stream(terminal_proc, websocket))

        while True:
            raw_msg = await websocket.receive_text()
            try:
                payload = json.loads(raw_msg)
                if payload['type'] == 'resize':
                    if terminal_proc:
                        manager.resize_terminal(terminal_proc, payload['cols'], payload['rows'])
                elif payload['type'] == 'input':
                    if terminal_proc:
                        await manager.write_stream(terminal_proc, payload['data'])
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        print("Client Disconnected")
    except Exception as e:
        print(f"Terminal Error: {e}")
    finally:
        if reader_task:
            reader_task.cancel()
        # Kill process logic could be improved here