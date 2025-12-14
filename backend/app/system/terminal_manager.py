import os
import platform
import asyncio

# Cek OS
IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    from winpty import PtyProcess
else:
    import pty
    import fcntl
    import struct
    import termios

class TerminalManager:
    def __init__(self):
        self.os_type = "windows" if IS_WINDOWS else "linux"

    def spawn_terminal(self):
        """
        Melahirkan process terminal baru.
        Windows -> cmd.exe
        Linux -> /bin/bash
        """
        if self.os_type == "windows":
            # Spawn CMD
            proc = PtyProcess.spawn(["cmd.exe"])
            return proc
        else:
            # Spawn Bash (Linux Logic)
            master_fd, slave_fd = pty.openpty()
            pid = os.fork()
            if pid == 0:
                os.setsid()
                os.dup2(slave_fd, 0)
                os.dup2(slave_fd, 1)
                os.dup2(slave_fd, 2)
                os.close(master_fd)
                os.close(slave_fd)
                os.execv("/bin/bash", ["/bin/bash"])
            else:
                os.close(slave_fd)
                return master_fd # Return File Descriptor

    async def read_stream(self, fd, websocket):
        """
        Membaca output dari terminal -> Kirim ke WebSocket (Frontend)
        """
        if self.os_type == "windows":
            while True:
                # Windows (pywinpty)
                try:
                    output = await asyncio.to_thread(fd.read, 1024)
                    if output:
                        await websocket.send_text(output)
                    else:
                        await asyncio.sleep(0.1)
                except Exception:
                    break
        else:
            # Linux (Native PTY)
            while True:
                await asyncio.sleep(0.01)
                try:
                    output = os.read(fd, 1024).decode(errors='ignore')
                    if output:
                        await websocket.send_text(output)
                except OSError:
                    break

    async def write_stream(self, fd, data):
        """
        Menerima input dari WebSocket (Ketik user) -> Tulis ke Terminal
        """
        if self.os_type == "windows":
            await asyncio.to_thread(fd.write, data)
        else:
            os.write(fd, data.encode())

    def resize_terminal(self, fd, cols: int, rows: int):
        """
        Mengubah ukuran terminal agar sinkron dengan browser.
        """
        if self.os_type == "windows":
            try:
                # [FIX FINAL] Kembalikan ke urutan standar: (rows, cols)
                # rows = Tinggi (misal 24)
                # cols = Lebar (misal 100)
                fd.setwinsize(rows, cols)
            except Exception as e:
                print(f"Resize Error (Windows): {e}")
        else:
            # Linux Logic (Tetap aman)
            import fcntl
            import struct
            import termios
            try:
                winsize = struct.pack("HHHH", rows, cols, 0, 0)
                fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
            except Exception as e:
                print(f"Resize Error (Linux): {e}")