"""Tests for key translation."""

from __future__ import annotations

from unittest.mock import MagicMock

from textual_term._keys import CTRL_KEYS, translate_key


class TestCtrlKeys:
    """Test the CTRL_KEYS mapping."""

    def test_arrow_keys_present(self) -> None:
        """Arrow keys should be in the mapping."""
        for key in ("up", "down", "left", "right"):
            assert key in CTRL_KEYS

    def test_function_keys_present(self) -> None:
        """Function keys F1-F12 should be in the mapping."""
        for i in range(1, 13):
            assert f"f{i}" in CTRL_KEYS

    def test_special_keys_present(self) -> None:
        """Tab, enter, backspace, escape should be in the mapping."""
        for key in ("tab", "enter", "backspace", "escape"):
            assert key in CTRL_KEYS

    def test_arrow_up_value(self) -> None:
        """Up arrow should map to ESC[A."""
        assert CTRL_KEYS["up"] == "\x1b[A"

    def test_enter_value(self) -> None:
        """Enter should map to carriage return."""
        assert CTRL_KEYS["enter"] == "\r"

    def test_backspace_value(self) -> None:
        """Backspace should map to DEL."""
        assert CTRL_KEYS["backspace"] == "\x7f"


class TestTranslateKey:
    """Test the translate_key function."""

    def test_translate_special_key(self) -> None:
        """Special keys should return their ANSI escape sequence."""
        event = MagicMock()
        event.key = "up"
        event.character = None
        assert translate_key(event) == "\x1b[A"

    def test_translate_character_key(self) -> None:
        """Regular character keys should return the character."""
        event = MagicMock()
        event.key = "a"
        event.character = "a"
        assert translate_key(event) == "a"

    def test_translate_unknown_key(self) -> None:
        """Unknown keys with no character should return None."""
        event = MagicMock()
        event.key = "unknown_special"
        event.character = None
        assert translate_key(event) is None
