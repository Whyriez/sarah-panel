import os
import platform
import asyncio

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

    def spawn_terminal(self, cwd=None):
        """
        Melahirkan process terminal baru.
        cwd: Current Working Directory (folder awal terminal)
        """
        # Default cwd jika tidak ada
        if not cwd or not os.path.exists(cwd):
            cwd = os.getcwd()  # Atau home directory user

        if self.os_type == "windows":
            # Windows: PtyProcess support argument cwd
            proc = PtyProcess.spawn(["cmd.exe"], cwd=cwd)
            return proc
        else:
            # Linux: Perlu os.chdir() di child process
            master_fd, slave_fd = pty.openpty()
            pid = os.fork()
            if pid == 0:
                # Child Process
                os.setsid()
                os.dup2(slave_fd, 0)
                os.dup2(slave_fd, 1)
                os.dup2(slave_fd, 2)
                os.close(master_fd)
                os.close(slave_fd)

                # [FIX] Pindah ke directory tujuan sebelum spawn bash
                try:
                    os.chdir(cwd)
                except:
                    pass  # Kalau gagal, tetep jalan di default dir

                # Set Environment variable biar terminal tau ini xterm
                os.environ["TERM"] = "xterm-256color"
                os.execv("/bin/bash", ["/bin/bash"])
            else:
                # Parent Process
                os.close(slave_fd)
                return master_fd

    async def read_stream(self, fd, websocket):
        if self.os_type == "windows":
            while True:
                try:
                    output = await asyncio.to_thread(fd.read, 1024)
                    if output:
                        await websocket.send_text(output)
                    else:
                        await asyncio.sleep(0.1)
                except Exception:
                    break
        else:
            while True:
                await asyncio.sleep(0.01)
                try:
                    output = os.read(fd, 1024).decode(errors='ignore')
                    if output:
                        await websocket.send_text(output)
                except OSError:
                    break

    async def write_stream(self, fd, data):
        if self.os_type == "windows":
            await asyncio.to_thread(fd.write, data)
        else:
            os.write(fd, data.encode())

    def resize_terminal(self, fd, cols: int, rows: int):
        if self.os_type == "windows":
            try:
                fd.setwinsize(rows, cols)
            except Exception as e:
                print(f"Resize Error: {e}")
        else:
            try:
                winsize = struct.pack("HHHH", rows, cols, 0, 0)
                fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
            except Exception as e:
                print(f"Resize Error: {e}")