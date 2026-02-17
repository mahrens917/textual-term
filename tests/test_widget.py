"""Tests for the Terminal widget."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from textual.events import Key, Resize
from textual.geometry import Size

from textual_term._renderer import TerminalRenderable
from textual_term._widget import DEFAULT_COLS, DEFAULT_ROWS, Terminal


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

    def test_render_returns_renderable(self) -> None:
        """render() should return the current TerminalRenderable."""
        terminal = Terminal(command="/bin/sh")
        result = terminal.render()
        assert isinstance(result, TerminalRenderable)

    def test_stop_without_start(self) -> None:
        """stop() should be safe to call when nothing is running."""
        terminal = Terminal(command="/bin/sh")
        terminal.stop()
        assert terminal._emulator is None
        assert terminal._recv_task is None

    def test_default_constants(self) -> None:
        """Default terminal size constants should be defined."""
        assert DEFAULT_ROWS == 24
        assert DEFAULT_COLS == 80


class TestTerminalStart:
    """Test Terminal.start() lifecycle."""

    @patch("textual_term._widget.asyncio.create_task")
    @patch("textual_term._widget.pyte.Stream")
    @patch("textual_term._widget.ResponsiveScreen")
    @patch("textual_term._widget.PtyEmulator")
    def test_start_creates_emulator_and_screen(
        self,
        mock_emulator_cls: MagicMock,
        mock_screen_cls: MagicMock,
        mock_stream_cls: MagicMock,
        mock_create_task: MagicMock,
    ) -> None:
        """start() should create emulator, screen, stream and begin recv loop."""
        terminal = Terminal(command="/bin/sh")

        mock_emulator = MagicMock()
        mock_emulator_cls.return_value = mock_emulator
        mock_screen = MagicMock()
        mock_screen_cls.return_value = mock_screen
        mock_stream = MagicMock()
        mock_stream_cls.return_value = mock_stream
        mock_create_task.return_value = MagicMock()

        with patch.object(Terminal, "size", new=property(lambda self: Size(80, 24))):
            terminal.start()

        mock_emulator_cls.assert_called_once_with("/bin/sh", 24, 80)
        mock_emulator.open_pty.assert_called_once()
        mock_emulator.start.assert_called_once()
        mock_screen_cls.assert_called_once_with(80, 24, write_callback=mock_emulator.write_to_pty)
        mock_stream_cls.assert_called_once_with(mock_screen)
        assert terminal._emulator is mock_emulator
        assert terminal._screen is mock_screen
        assert terminal._stream is mock_stream


class TestTerminalStop:
    """Test Terminal.stop() cleanup."""

    def test_stop_cancels_recv_task(self) -> None:
        """stop() should cancel the recv task."""
        terminal = Terminal(command="/bin/sh")
        mock_task = MagicMock()
        terminal._recv_task = mock_task
        terminal._emulator = MagicMock()

        terminal.stop()

        mock_task.cancel.assert_called_once()
        assert terminal._recv_task is None

    def test_stop_stops_emulator(self) -> None:
        """stop() should stop the emulator."""
        terminal = Terminal(command="/bin/sh")
        mock_emulator = MagicMock()
        terminal._emulator = mock_emulator

        terminal.stop()

        mock_emulator.stop.assert_called_once()
        assert terminal._emulator is None


class TestTerminalRecvLoop:
    """Test the _recv_loop coroutine."""

    async def test_recv_loop_exits_when_no_emulator(self) -> None:
        """_recv_loop should return immediately if emulator is None."""
        terminal = Terminal(command="/bin/sh")
        await terminal._recv_loop()

    async def test_recv_loop_processes_stdout(self) -> None:
        """_recv_loop should feed stdout data to the stream and refresh."""
        terminal = Terminal(command="/bin/sh")
        mock_emulator = MagicMock()
        mock_stream = MagicMock()
        mock_screen = MagicMock()
        mock_screen.cursor = MagicMock(x=0, y=0)
        mock_screen.lines = 1
        mock_screen.columns = 1
        mock_screen.buffer = {
            0: {
                0: MagicMock(
                    data=" ", fg="default", bg="default", bold=False, italics=False, underscore=False, strikethrough=False, reverse=False
                )
            }
        }

        queue: asyncio.Queue[list] = asyncio.Queue()  # pyright: ignore[reportMissingTypeArgument]
        await queue.put(["stdout", "hello"])
        await queue.put(["disconnect", 1])
        mock_emulator.output_queue = queue

        terminal._emulator = mock_emulator
        terminal._stream = mock_stream
        terminal._screen = mock_screen
        terminal.refresh = MagicMock()

        await terminal._recv_loop()

        mock_stream.feed.assert_called_once_with("hello")
        terminal.refresh.assert_called_once()

    async def test_recv_loop_breaks_on_disconnect(self) -> None:
        """_recv_loop should break when it receives a disconnect message."""
        terminal = Terminal(command="/bin/sh")
        mock_emulator = MagicMock()
        mock_stream = MagicMock()
        mock_screen = MagicMock()

        queue: asyncio.Queue[list] = asyncio.Queue()  # pyright: ignore[reportMissingTypeArgument]
        await queue.put(["disconnect", 1])
        mock_emulator.output_queue = queue

        terminal._emulator = mock_emulator
        terminal._stream = mock_stream
        terminal._screen = mock_screen

        await terminal._recv_loop()
        mock_stream.feed.assert_not_called()


class TestTerminalOnKey:
    """Test the on_key handler."""

    async def test_on_key_no_emulator(self) -> None:
        """on_key should return early if no emulator is set."""
        terminal = Terminal(command="/bin/sh")
        event = MagicMock(spec=Key)
        await terminal.on_key(event)
        event.stop.assert_not_called()

    async def test_on_key_translates_and_sends(self) -> None:
        """on_key should translate the key and put it on the input queue."""
        terminal = Terminal(command="/bin/sh")
        mock_emulator = MagicMock()
        mock_emulator.input_queue = AsyncMock()
        terminal._emulator = mock_emulator

        event = MagicMock(spec=Key)
        event.key = "enter"
        event.character = "\r"

        with patch("textual_term._widget.translate_key", return_value="\r"):
            await terminal.on_key(event)

        event.stop.assert_called_once()
        mock_emulator.input_queue.put.assert_called_once_with(["stdin", "\r"])

    async def test_on_key_untranslatable(self) -> None:
        """on_key should not send anything if translate_key returns None."""
        terminal = Terminal(command="/bin/sh")
        mock_emulator = MagicMock()
        mock_emulator.input_queue = AsyncMock()
        terminal._emulator = mock_emulator

        event = MagicMock(spec=Key)
        event.key = "unknown"
        event.character = None

        with patch("textual_term._widget.translate_key", return_value=None):
            await terminal.on_key(event)

        event.stop.assert_called_once()
        mock_emulator.input_queue.put.assert_not_called()


class TestTerminalOnResize:
    """Test the on_resize handler."""

    async def test_on_resize_updates_screen(self) -> None:
        """on_resize should resize the screen and notify the emulator."""
        terminal = Terminal(command="/bin/sh")

        mock_screen = MagicMock()
        mock_screen.lines = 24
        mock_screen.columns = 80
        mock_emulator = MagicMock()
        mock_emulator.input_queue = AsyncMock()
        terminal._screen = mock_screen
        terminal._emulator = mock_emulator

        event = MagicMock(spec=Resize)
        with patch.object(Terminal, "size", new=property(lambda self: Size(120, 40))):
            await terminal.on_resize(event)

        mock_screen.resize.assert_called_once_with(40, 120)
        mock_emulator.input_queue.put.assert_called_once_with(["resize", 40, 120])

    async def test_on_resize_no_change(self) -> None:
        """on_resize should not resize if dimensions are unchanged."""
        terminal = Terminal(command="/bin/sh")

        mock_screen = MagicMock()
        mock_screen.lines = 24
        mock_screen.columns = 80
        terminal._screen = mock_screen

        event = MagicMock(spec=Resize)
        with patch.object(Terminal, "size", new=property(lambda self: Size(80, 24))):
            await terminal.on_resize(event)

        mock_screen.resize.assert_not_called()

    async def test_on_resize_no_screen(self) -> None:
        """on_resize should be safe when no screen exists."""
        terminal = Terminal(command="/bin/sh")

        event = MagicMock(spec=Resize)
        with patch.object(Terminal, "size", new=property(lambda self: Size(120, 40))):
            await terminal.on_resize(event)


class TestTerminalSize:
    """Test the _terminal_size helper."""

    def test_terminal_size_from_widget(self) -> None:
        """_terminal_size should return widget dimensions when valid."""
        terminal = Terminal(command="/bin/sh")
        with patch.object(Terminal, "size", new=property(lambda self: Size(100, 50))):
            rows, cols = terminal._terminal_size()
        assert rows == 50
        assert cols == 100

    def test_terminal_size_defaults_when_small(self) -> None:
        """_terminal_size should use defaults when widget size is 1 or less."""
        terminal = Terminal(command="/bin/sh")
        with patch.object(Terminal, "size", new=property(lambda self: Size(0, 0))):
            rows, cols = terminal._terminal_size()
        assert rows == DEFAULT_ROWS
        assert cols == DEFAULT_COLS

    def test_terminal_size_partial_default(self) -> None:
        """_terminal_size should default only the dimension that is too small."""
        terminal = Terminal(command="/bin/sh")
        with patch.object(Terminal, "size", new=property(lambda self: Size(1, 50))):
            rows, cols = terminal._terminal_size()
        assert rows == 50
        assert cols == DEFAULT_COLS
