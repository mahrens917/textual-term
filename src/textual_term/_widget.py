"""Textual Terminal widget with embedded PTY and batched rendering."""

from __future__ import annotations

import asyncio

import pyte
from textual.events import Key, Resize
from textual.widget import Widget

from textual_term._emulator import PtyEmulator
from textual_term._keys import translate_key
from textual_term._renderer import TerminalRenderable, render_screen
from textual_term._screen import ResponsiveScreen

DEFAULT_ROWS = 24
DEFAULT_COLS = 80


class Terminal(Widget, can_focus=True):
    """Terminal emulator widget that runs a command in a PTY."""

    DEFAULT_CSS = """
    Terminal {
        height: 1fr;
    }
    """

    def __init__(
        self,
        command: str,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._command = command
        self._emulator: PtyEmulator | None = None
        self._screen: ResponsiveScreen | None = None
        self._stream: pyte.Stream | None = None
        self._recv_task: asyncio.Task | None = None  # pyright: ignore[reportMissingTypeArgument]
        self._renderable = TerminalRenderable([])

    def start(self) -> None:
        """Start the PTY emulator and begin processing output."""
        rows, cols = self._terminal_size()
        emulator = PtyEmulator(self._command, rows, cols)
        emulator.open_pty()
        screen = ResponsiveScreen(cols, rows, write_callback=emulator.write_to_pty)
        stream = pyte.Stream(screen)
        self._emulator = emulator
        self._screen = screen
        self._stream = stream
        emulator.start()
        self._recv_task = asyncio.create_task(self._recv_loop())

    def stop(self) -> None:
        """Stop the PTY emulator and cancel background tasks."""
        if self._recv_task:
            self._recv_task.cancel()
            self._recv_task = None
        if self._emulator:
            self._emulator.stop()
            self._emulator = None

    def render(self) -> TerminalRenderable:
        """Return the current terminal renderable."""
        return self._renderable

    async def _recv_loop(self) -> None:
        """Drain emulator output_queue, feed to pyte, and refresh display."""
        emulator = self._emulator
        stream = self._stream
        screen = self._screen
        if emulator is None or stream is None or screen is None:
            return
        while True:
            msg = await emulator.output_queue.get()
            if msg[0] == "stdout":
                stream.feed(msg[1])
                self._renderable = TerminalRenderable(render_screen(screen, self.has_focus))
                self.refresh()
            elif msg[0] == "disconnect":
                break

    async def on_key(self, event: Key) -> None:
        """Translate key event and write to PTY."""
        if self._emulator is None:
            return
        event.stop()
        translated = translate_key(event)
        if translated is not None:
            await self._emulator.input_queue.put(["stdin", translated])

    async def on_resize(self, event: Resize) -> None:
        """Update screen size and notify PTY of resize."""
        rows, cols = self._terminal_size()
        if self._screen and (self._screen.lines != rows or self._screen.columns != cols):
            self._screen.resize(rows, cols)
            if self._emulator:
                await self._emulator.input_queue.put(["resize", rows, cols])

    def _terminal_size(self) -> tuple[int, int]:
        """Return (rows, cols) from widget content size, defaulting to 80x24."""
        height = self.size.height
        width = self.size.width
        rows = height if height > 1 else DEFAULT_ROWS
        cols = width if width > 1 else DEFAULT_COLS
        return rows, cols
