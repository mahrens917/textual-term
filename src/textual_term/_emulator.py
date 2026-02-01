"""Async PTY subprocess manager with I/O queues."""

from __future__ import annotations

import asyncio
import contextlib
import os

from textual_term._pty import close_pty, open_pty, resize_fd, write_to_fd

_EOF_SENTINEL = ""


class PtyEmulator:
    """Manages a child process via pty with async I/O."""

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
        self._pid, self._fd = open_pty(self._command, self._rows, self._cols)

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
            with contextlib.suppress(ValueError, OSError):
                loop.remove_reader(fd)
        close_pty(self._fd, self._pid)
        self._fd = None
        self._pid = None

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

    async def _reader_loop(self) -> None:
        """Read from PTY fd and put data on output_queue."""
        loop = asyncio.get_event_loop()
        fd = self._fd
        if fd is None:
            return
        read_event = asyncio.Event()
        loop.add_reader(fd, read_event.set)
        try:
            while True:
                await read_event.wait()
                read_event.clear()
                data = _safe_read(fd)
                if data is _EOF_SENTINEL:
                    break
                await self.output_queue.put(["stdout", data])
        finally:
            with contextlib.suppress(ValueError, OSError):
                loop.remove_reader(fd)

    async def _writer_loop(self) -> None:
        """Drain input_queue and dispatch messages to PTY."""
        while True:
            msg = await self.input_queue.get()
            if msg[0] == "stdin":
                self.write_to_pty(msg[1])
            elif msg[0] == "resize":
                self.resize(msg[1], msg[2])


def _safe_read(fd: int) -> str:
    """Read from fd, returning _EOF_SENTINEL on error or EOF."""
    with contextlib.suppress(OSError):
        data = os.read(fd, 65536)
        if data:
            return data.decode("utf-8", errors="replace")
    return _EOF_SENTINEL
