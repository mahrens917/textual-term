"""Pyte Screen subclass that writes DSR responses back to the PTY."""

from __future__ import annotations

from collections.abc import Callable

import pyte


class ResponsiveScreen(pyte.Screen):
    """Pyte Screen that writes DSR responses back to the PTY.

    When a child process sends ESC[6n (cursor position request), pyte calls
    report_device_status() which calls write_process_input() with the response.
    The base pyte implementation is a no-op. This subclass writes the response
    back to the PTY fd so the child process receives the answer.
    """

    def __init__(self, columns: int, lines: int, write_callback: Callable[[str], None]) -> None:
        super().__init__(columns, lines)
        self._write_callback = write_callback

    def write_process_input(self, data: str) -> None:
        """Write DSR response data back to the PTY stdin."""
        self._write_callback(data)

    def set_margins(self, *args: int, **kwargs: bool) -> None:
        """Override to strip the 'private' kwarg that pyte may pass."""
        kwargs.pop("private", None)
        super().set_margins(*args, **kwargs)
