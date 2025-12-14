from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.system.terminal_manager import TerminalManager
from app.core.security import SECRET_KEY, ALGORITHM
from jose import jwt
import json

router = APIRouter(tags=["Terminal"])

manager = TerminalManager()


# WebSocket tidak support Header Authorization standar.
# Kita kirim token lewat Query Param: ws://localhost:8000/ws/terminal?token=...
async def get_token_from_ws(websocket: WebSocket):
    token = websocket.query_params.get("token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")  # Return username
    except:
        return None


@router.websocket("/ws/terminal")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    user = await get_token_from_ws(websocket)
    if not user:
        await websocket.send_text("Error: Unauthorized\r\n")
        await websocket.close()
        return

    reader_task = None
    terminal_proc = None

    try:
        # 1. Tunggu Handshake Ukuran dari Frontend
        initial_msg = await websocket.receive_text()
        initial_config = json.loads(initial_msg)

        cols = 80
        rows = 24
        if initial_config.get('type') == 'resize':
            cols = initial_config['cols']
            rows = initial_config['rows']

        # 2. Spawn Terminal
        terminal_proc = manager.spawn_terminal()

        # 3. Resize Sesuai Ukuran Frontend
        manager.resize_terminal(terminal_proc, cols, rows)

        # 4. [JURUS PAMUNGKAS] Auto Clear Screen
        # Kita kirim perintah 'cls' + Enter ke terminal biar layarnya bersih & cursor reset
        await manager.write_stream(terminal_proc, "cls\r")

        # 5. Kirim Pesan Selamat Datang (Opsional, akan muncul setelah layar bersih)
        # Kasih jeda dikit biar gak kehapus sama CLS
        import asyncio
        await asyncio.sleep(0.1)
        await websocket.send_text(f"\x1b[32m✅ Connected to AlimPanel Shell...\x1b[0m\r\n")
        # --- [LOGIC BARU END] ---

        # Background task baca output terminal
        import asyncio
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