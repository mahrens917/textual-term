"""Tests for DSR (Device Status Report) responses via ResponsiveScreen."""

from __future__ import annotations

import pyte

from textual_term._screen import ResponsiveScreen


class TestDsrCursorPosition:
    """Test ESC[6n cursor position report."""

    def test_cursor_position_response(self) -> None:
        """ESC[6n should produce a cursor position response."""
        responses: list[str] = []
        screen = ResponsiveScreen(80, 24, write_callback=responses.append)
        stream = pyte.Stream(screen)
        stream.feed("\x1b[6n")
        assert len(responses) == 1
        assert responses[0] == "\x1b[1;1R"

    def test_cursor_position_after_move(self) -> None:
        """Cursor position response should reflect cursor movement."""
        responses: list[str] = []
        screen = ResponsiveScreen(80, 24, write_callback=responses.append)
        stream = pyte.Stream(screen)
        stream.feed("\x1b[5;10H")
        stream.feed("\x1b[6n")
        assert len(responses) == 1
        assert responses[0] == "\x1b[5;10R"

    def test_device_status_ok(self) -> None:
        """ESC[5n should produce a 'device OK' response."""
        responses: list[str] = []
        screen = ResponsiveScreen(80, 24, write_callback=responses.append)
        stream = pyte.Stream(screen)
        stream.feed("\x1b[5n")
        assert len(responses) == 1
        assert responses[0] == "\x1b[0n"


class TestDsrDeviceAttributes:
    """Test ESC[c device attributes report."""

    def test_device_attributes_response(self) -> None:
        """ESC[c should produce a device attributes response."""
        responses: list[str] = []
        screen = ResponsiveScreen(80, 24, write_callback=responses.append)
        stream = pyte.Stream(screen)
        stream.feed("\x1b[c")
        assert len(responses) == 1
        assert "\x1b[?" in responses[0]


class TestSetMargins:
    """Test set_margins private kwarg stripping."""

    def test_set_margins_with_private(self) -> None:
        """set_margins should work even when private kwarg is passed."""
        responses: list[str] = []
        screen = ResponsiveScreen(80, 24, write_callback=responses.append)
        screen.set_margins(1, 24, private=True)

    def test_set_margins_without_private(self) -> None:
        """set_margins should work normally without private kwarg."""
        responses: list[str] = []
        screen = ResponsiveScreen(80, 24, write_callback=responses.append)
        screen.set_margins(1, 24)
