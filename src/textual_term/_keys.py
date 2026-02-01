"""Key translation from Textual key events to ANSI escape sequences."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from textual.events import Key

CTRL_KEYS: dict[str, str] = {
    "up": "\x1b[A",
    "down": "\x1b[B",
    "right": "\x1b[C",
    "left": "\x1b[D",
    "home": "\x1b[H",
    "end": "\x1b[F",
    "insert": "\x1b[2~",
    "delete": "\x1b[3~",
    "pageup": "\x1b[5~",
    "pagedown": "\x1b[6~",
    "f1": "\x1bOP",
    "f2": "\x1bOQ",
    "f3": "\x1bOR",
    "f4": "\x1bOS",
    "f5": "\x1b[15~",
    "f6": "\x1b[17~",
    "f7": "\x1b[18~",
    "f8": "\x1b[19~",
    "f9": "\x1b[20~",
    "f10": "\x1b[21~",
    "f11": "\x1b[23~",
    "f12": "\x1b[24~",
    "tab": "\t",
    "enter": "\r",
    "backspace": "\x7f",
    "escape": "\x1b",
}


def translate_key(event: Key) -> str | None:
    """Translate a Textual Key event to a string suitable for PTY input.

    Returns None if the key cannot be translated.
    """
    if event.key in CTRL_KEYS:
        return CTRL_KEYS[event.key]
    if event.character:
        return event.character
    return None
