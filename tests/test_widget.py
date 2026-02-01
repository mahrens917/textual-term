"""Tests for the Terminal widget."""

from __future__ import annotations

from textual_term._widget import Terminal


class TestTerminalWidget:
    """Test Terminal widget construction."""

    def test_create_terminal(self) -> None:
        """Terminal should be constructible with a command string."""
        terminal = Terminal(command="/bin/sh", id="test-term")
        assert terminal._command == "/bin/sh"

    def test_initial_state(self) -> None:
        """Terminal should start with no emulator or screen."""
        terminal = Terminal(command="/bin/sh")
        assert terminal._emulator is None
        assert terminal._screen is None
        assert terminal._stream is None
