"""Async PTY subprocess manager with I/O queues."""

from __future__ import annotations

import asyncio
import contextlib
import os

from textual_term._pty import close_pty, open_pty, resize_fd, write_to_fd


class PtyEmulator:
    """Manages a child process via pty with async I/O."""

    def __init__(self, command: str, rows: int, cols: int) -> None:
        self._command = command
        self._rows = rows
        self._cols = cols
        self._fd: int | None = None
        self._pid: int | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._run_task: asyncio.Task | None = None  # pyright: ignore[reportMissingTypeArgument]
        self.input_queue: asyncio.Queue[list] = asyncio.Queue()  # pyright: ignore[reportMissingTypeArgument]
        self.output_queue: asyncio.Queue[list] = asyncio.Queue()  # pyright: ignore[reportMissingTypeArgument]

    def open_pty(self) -> None:
        """Fork a PTY and exec the command in the child process."""
        self._pid, self._fd = open_pty(self._command, self._rows, self._cols)

    def start(self) -> None:
        """Create run asyncio task."""
        self._run_task = asyncio.create_task(self._run())

    def stop(self) -> None:
        """Cancel tasks, remove reader, kill child, reap zombie."""
        if self._run_task:
            self._run_task.cancel()
            self._run_task = None
        if self._loop and self._fd is not None:
            with contextlib.suppress(ValueError, OSError):
                self._loop.remove_reader(self._fd)
        close_pty(self._fd, self._pid)
        self._fd = None
        self._pid = None
        self._loop = None

    def write_to_pty(self, data: str) -> None:
        """Write raw string data to the PTY fd."""
        if self._fd is not None:
            write_to_fd(self._fd, data)

    def resize(self, rows: int, cols: int) -> None:
        """Resize the PTY window."""
        self._rows = rows
        self._cols = cols
        if self._fd is not None:
            resize_fd(self._fd, rows, cols)

    async def _run(self) -> None:
        """Register PTY reader and handle input from widget."""
        loop = asyncio.get_running_loop()
        self._loop = loop
        fd = self._fd
        if fd is None:
            return

        def on_output() -> None:
            raw = _read_pty_bytes(fd)
            if raw is None:
                with contextlib.suppress(OSError, ValueError):
                    loop.remove_reader(fd)
                self.output_queue.put_nowait(["disconnect", 1])
                return
            self.output_queue.put_nowait(["stdout", raw.decode("utf-8", errors="replace")])

        loop.add_reader(fd, on_output)
        while True:
            msg = await self.input_queue.get()
            if msg[0] == "stdin":
                self.write_to_pty(msg[1])
            elif msg[0] == "resize":
                self.resize(msg[1], msg[2])


def _read_pty_bytes(fd: int) -> bytes | None:
    """Read raw bytes from PTY fd. Returns None on EOF or error."""
    with contextlib.suppress(OSError, ValueError):
        data = os.read(fd, 65536)
        if data:
            return data
    return None
