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
        self._p_out = None  # file object wrapping PTY fd, set by open_pty()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._run_task: asyncio.Task | None = None  # pyright: ignore[reportMissingTypeArgument]
        self._send_task: asyncio.Task | None = None  # pyright: ignore[reportMissingTypeArgument]
        self._data_or_disconnect: str | None = None
        self._event = asyncio.Event()
        self.input_queue: asyncio.Queue[list] = asyncio.Queue()  # pyright: ignore[reportMissingTypeArgument]
        self.output_queue: asyncio.Queue[list] = asyncio.Queue()  # pyright: ignore[reportMissingTypeArgument]

    def open_pty(self) -> None:
        """Fork a PTY and exec the command in the child process."""
        self._pid, self._fd = open_pty(self._command, self._rows, self._cols)
        self._p_out = os.fdopen(self._fd, "w+b", 0)

    def start(self) -> None:
        """Create run and send asyncio tasks."""
        self._run_task = asyncio.create_task(self._run())
        self._send_task = asyncio.create_task(self._send_data())

    def stop(self) -> None:
        """Cancel tasks, remove reader, kill child, reap zombie."""
        if self._run_task:
            self._run_task.cancel()
            self._run_task = None
        if self._send_task:
            self._send_task.cancel()
            self._send_task = None
        if self._loop and self._p_out:
            with contextlib.suppress(ValueError, OSError):
                self._loop.remove_reader(self._p_out)
        close_pty(self._fd, self._pid)
        self._fd = None
        self._pid = None
        self._p_out = None
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
        p_out = self._p_out
        if p_out is None:
            return

        def on_output() -> None:
            raw = _read_pty_bytes(p_out)
            if raw is None:
                with contextlib.suppress(OSError, ValueError):
                    loop.remove_reader(p_out)
                self._data_or_disconnect = None
                self._event.set()
                return
            self._data_or_disconnect = raw.decode("utf-8", errors="replace")
            self._event.set()

        loop.add_reader(p_out, on_output)
        while True:
            msg = await self.input_queue.get()
            if msg[0] == "stdin":
                self.write_to_pty(msg[1])
            elif msg[0] == "resize":
                self.resize(msg[1], msg[2])

    async def _send_data(self) -> None:
        """Forward PTY output data to the output queue."""
        while True:
            await self._event.wait()
            self._event.clear()
            if self._data_or_disconnect is not None:
                await self.output_queue.put(["stdout", self._data_or_disconnect])
            else:
                await self.output_queue.put(["disconnect", 1])
                break


def _read_pty_bytes(p_out: object) -> bytes | None:
    """Read raw bytes from PTY file object. Returns None on EOF or error."""
    with contextlib.suppress(OSError, ValueError):
        data = p_out.read(65536)  # pyright: ignore[reportAttributeAccessIssue]
        if data:
            return data  # pyright: ignore[reportReturnType]
    return None
