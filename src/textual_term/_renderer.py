"""Pyte screen buffer to Rich Text rendering."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import ConsoleOptions, RenderResult
from rich.style import Style
from rich.text import Text

if TYPE_CHECKING:
    from pyte.screens import Char, Screen
    from rich.console import Console

COLOR_MAP: dict[str, str] = {
    "brown": "yellow",
    "brightblack": "#808080",
    "brightred": "bright_red",
    "brightgreen": "bright_green",
    "brightyellow": "bright_yellow",
    "brightblue": "bright_blue",
    "brightmagenta": "bright_magenta",
    "brightcyan": "bright_cyan",
    "brightwhite": "bright_white",
}


def _resolve_color(color: str) -> str | None:
    """Convert a pyte color name to a Rich color string."""
    if not color:
        return None
    lower = color.lower()
    if lower in COLOR_MAP:
        return COLOR_MAP[lower]
    hex_color_length = 6
    if len(color) == hex_color_length and all(c in "0123456789abcdefABCDEF" for c in color):
        return f"#{color}"
    return lower


def _char_to_style(char: Char) -> Style:
    """Convert a pyte Char to a Rich Style."""
    fg = _resolve_color(char.fg) if char.fg != "default" else None
    bg = _resolve_color(char.bg) if char.bg != "default" else None
    return Style(
        color=fg,
        bgcolor=bg,
        bold=char.bold,
        italic=char.italics,
        underline=char.underscore,
        strike=char.strikethrough,
        reverse=char.reverse,
    )


def _render_line(
    line: dict[int, Char],
    columns: int,
    cursor_x: int | None,
) -> Text:
    """Render a single screen line to a Rich Text object."""
    text = Text()
    for x in range(columns):
        char = line.get(x)
        if char is None:
            if cursor_x == x:
                text.append(" ", Style(reverse=True))
            else:
                text.append(" ")
            continue
        style = _char_to_style(char)
        if cursor_x == x:
            style = style + Style(reverse=True)
        text.append(char.data, style)
    return text


def render_screen(screen: Screen, show_cursor: bool) -> list[Text]:
    """Convert a pyte Screen buffer to a list of Rich Text lines."""
    lines: list[Text] = []
    cursor_y = screen.cursor.y if show_cursor else -1
    for y in range(screen.lines):
        cursor_x = screen.cursor.x if y == cursor_y else None
        lines.append(_render_line(screen.buffer[y], screen.columns, cursor_x))
    return lines


class TerminalRenderable:
    """Rich renderable wrapper for terminal screen content."""

    def __init__(self, text_lines: list[Text]) -> None:
        self._lines = text_lines

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        yield from self._lines
