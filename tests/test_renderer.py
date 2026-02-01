"""Tests for the terminal renderer."""

from __future__ import annotations

import pyte
from pyte.screens import Char
from rich.text import Text

from textual_term._renderer import (
    TerminalRenderable,
    _char_to_style,
    _resolve_color,
    render_screen,
)


class TestResolveColor:
    """Test color name resolution."""

    def test_empty_color(self) -> None:
        """Empty string should return None."""
        assert _resolve_color("") is None

    def test_brown_maps_to_yellow(self) -> None:
        """Brown should map to yellow."""
        assert _resolve_color("brown") == "yellow"

    def test_brightblack_maps_to_gray(self) -> None:
        """Brightblack should map to #808080."""
        assert _resolve_color("brightblack") == "#808080"

    def test_hex_color(self) -> None:
        """Six-digit hex string should get # prefix."""
        assert _resolve_color("ff0000") == "#ff0000"

    def test_named_color_passthrough(self) -> None:
        """Standard color names should pass through lowercase."""
        assert _resolve_color("red") == "red"

    def test_brightgreen_maps_correctly(self) -> None:
        """Brightgreen should map to bright_green."""
        assert _resolve_color("brightgreen") == "bright_green"


class TestCharToStyle:
    """Test pyte Char to Rich Style conversion."""

    def test_default_char(self) -> None:
        """Default char should produce empty style."""
        char = Char(" ")
        style = _char_to_style(char)
        assert style.color is None
        assert style.bgcolor is None

    def test_bold_char(self) -> None:
        """Bold char should produce bold style."""
        char = Char("X", bold=True)
        style = _char_to_style(char)
        assert style.bold is True

    def test_colored_char(self) -> None:
        """Char with fg color should produce colored style."""
        char = Char("X", fg="red")
        style = _char_to_style(char)
        assert style.color is not None


class TestRenderScreen:
    """Test full screen rendering."""

    def test_empty_screen(self) -> None:
        """An empty screen should produce lines of spaces."""
        screen = pyte.Screen(10, 3)
        lines = render_screen(screen, show_cursor=False)
        assert len(lines) == 3
        for line in lines:
            assert isinstance(line, Text)

    def test_screen_with_text(self) -> None:
        """Text written to screen should appear in rendered output."""
        screen = pyte.Screen(20, 3)
        stream = pyte.Stream(screen)
        stream.feed("hello")
        lines = render_screen(screen, show_cursor=False)
        assert "hello" in lines[0].plain

    def test_cursor_rendering(self) -> None:
        """Cursor position should get reverse style when show_cursor is True."""
        screen = pyte.Screen(10, 3)
        lines = render_screen(screen, show_cursor=True)
        first_line = lines[0]
        spans = first_line._spans
        assert any(span.style.reverse for span in spans if hasattr(span.style, "reverse") and span.style.reverse)


class TestTerminalRenderable:
    """Test the TerminalRenderable wrapper."""

    def test_rich_console_yields_lines(self) -> None:
        """__rich_console__ should yield the text lines."""
        text_lines = [Text("line1"), Text("line2")]
        renderable = TerminalRenderable(text_lines)
        from unittest.mock import MagicMock

        console = MagicMock()
        options = MagicMock()
        result = list(renderable.__rich_console__(console, options))
        assert len(result) == 2
        assert result[0].plain == "line1"
