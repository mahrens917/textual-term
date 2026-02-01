"""Textual Terminal widget with embedded PTY and batched rendering."""

from __future__ import annotations

import asyncio

import pyte
from textual.events import Key, Resize
from textual.timer import Timer
from textual.widget import Widget

from textual_term._emulator import PtyEmulator
from textual_term._keys import translate_key
from textual_term._renderer import TerminalRenderable, render_screen
from textual_term._screen import ResponsiveScreen

REFRESH_RATE = 1 / 30


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
        self._refresh_timer: Timer | None = None
        self._needs_render = False
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
        loop = asyncio.get_event_loop()
        self._recv_task = loop.create_task(self._recv_loop())
        self._refresh_timer = self.set_interval(REFRESH_RATE, self._on_refresh_tick)

    async def stop(self) -> None:
        """Stop the PTY emulator and cancel background tasks."""
        if self._recv_task:
            self._recv_task.cancel()
            self._recv_task = None
        if self._refresh_timer:
            self._refresh_timer.stop()
            self._refresh_timer = None
        if self._emulator:
            await self._emulator.stop()
            self._emulator = None

    def render(self) -> TerminalRenderable:
        """Return the current terminal renderable."""
        return self._renderable

    def _on_refresh_tick(self) -> None:
        if self._needs_render and self._screen:
            self._needs_render = False
            self._renderable = TerminalRenderable(render_screen(self._screen, self.has_focus))
            self.refresh()

    async def _recv_loop(self) -> None:
        """Drain emulator output_queue and feed to pyte Stream."""
        emulator = self._emulator
        stream = self._stream
        if emulator is None or stream is None:
            return
        while True:
            msg = await emulator.output_queue.get()
            if msg[0] == "stdout":
                stream.feed(msg[1])
                self._needs_render = True

    async def on_key(self, event: Key) -> None:
        """Translate key event and write to PTY."""
        event.prevent_default()
        event.stop()
        translated = translate_key(event)
        if translated is not None and self._emulator:
            await self._emulator.input_queue.put(["stdin", translated])

    def on_resize(self, event: Resize) -> None:
        """Update screen size and notify PTY of resize."""
        rows, cols = self._terminal_size()
        if self._screen and (self._screen.lines != rows or self._screen.columns != cols):
            self._screen.resize(rows, cols)
            if self._emulator:
                self._emulator.resize(rows, cols)

    def _terminal_size(self) -> tuple[int, int]:
        """Return (rows, cols) from widget content size."""
        rows = max(self.content_size.height, 2)
        cols = max(self.content_size.width, 2)
        return rows, cols
