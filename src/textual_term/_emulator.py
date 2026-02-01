"""PTY subprocess manager with async I/O queues."""

from __future__ import annotations

import asyncio
import fcntl
import os
import pty
import signal
import struct
import termios


class PtyEmulator:
    """Manages a child process via pty.fork() with async I/O."""

    def __init__(self, command: str, rows: int, cols: int) -> None:
        self._command = command
        self._rows = rows
        self._cols = cols
        self._fd: int | None = None
        self._pid: int | None = None
        self._reader_task: asyncio.Task | None = None  # pyright: ignore[reportMissingTypeArgument]
        self._writer_task: asyncio.Task | None = None  # pyright: ignore[reportMissingTypeArgument]
        self.input_queue: asyncio.Queue[list] = asyncio.Queue()  # pyright: ignore[reportMissingTypeArgument]
        self.output_queue: asyncio.Queue[list] = asyncio.Queue()  # pyright: ignore[reportMissingTypeArgument]

    def open_pty(self) -> None:
        """Fork a PTY and exec the command in the child process."""
        pid, fd = pty.openpty()
        self._fd = fd
        self._resize_fd(self._rows, self._cols)
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        child_pid = os.fork()
        if child_pid == 0:
            os.close(fd)
            os.setsid()
            _slave_fd = pid
            for i in range(3):
                os.dup2(_slave_fd, i)
            if _slave_fd > 2:
                os.close(_slave_fd)
            shell = self._command
            os.execvpe(shell, [shell], env)
        else:
            os.close(pid)
            self._pid = child_pid

    def start(self) -> None:
        """Create reader and writer asyncio tasks."""
        loop = asyncio.get_event_loop()
        self._reader_task = loop.create_task(self._reader_loop())
        self._writer_task = loop.create_task(self._writer_loop())

    async def stop(self) -> None:
        """Cancel tasks, close fd, kill child, reap zombie."""
        if self._reader_task:
            self._reader_task.cancel()
            self._reader_task = None
        if self._writer_task:
            self._writer_task.cancel()
            self._writer_task = None
        fd = self._fd
        if fd is not None:
            loop = asyncio.get_event_loop()
            try:
                loop.remove_reader(fd)
            except (ValueError, OSError):
                pass
            try:
                os.close(fd)
            except OSError:
                pass
            self._fd = None
        pid = self._pid
        if pid is not None:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                pass
            self._pid = None

    def write_to_pty(self, data: str) -> None:
        """Write raw string data to the PTY fd."""
        if self._fd is not None:
            os.write(self._fd, data.encode("utf-8"))

    def resize(self, rows: int, cols: int) -> None:
        """Resize the PTY window."""
        self._rows = rows
        self._cols = cols
        self._resize_fd(rows, cols)

    def _resize_fd(self, rows: int, cols: int) -> None:
        if self._fd is not None:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self._fd, termios.TIOCSWINSZ, winsize)

    async def _reader_loop(self) -> None:
        """Read from PTY fd and put data on output_queue."""
        loop = asyncio.get_event_loop()
        fd = self._fd
        if fd is None:
            return
        read_event = asyncio.Event()

        def _on_readable() -> None:
            read_event.set()

        loop.add_reader(fd, _on_readable)
        try:
            while True:
                await read_event.wait()
                read_event.clear()
                try:
                    data = os.read(fd, 65536)
                except OSError:
                    break
                if not data:
                    break
                await self.output_queue.put(["stdout", data.decode("utf-8", errors="replace")])
        except asyncio.CancelledError:
            pass
        finally:
            try:
                loop.remove_reader(fd)
            except (ValueError, OSError):
                pass

    async def _writer_loop(self) -> None:
        """Drain input_queue and dispatch messages to PTY."""
        try:
            while True:
                msg = await self.input_queue.get()
                if msg[0] == "stdin":
                    self.write_to_pty(msg[1])
                elif msg[0] == "resize":
                    self.resize(msg[1], msg[2])
        except asyncio.CancelledError:
            pass
