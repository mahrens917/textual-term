# textual-term

Terminal emulator widget for [Textual](https://github.com/Textualize/textual) with DSR (Device Status Report) support.

Embeds a fully interactive PTY terminal inside Textual applications. Unlike [textual-terminal](https://github.com/mitosch/textual-terminal), this widget supports DSR responses, which means TUI programs that query cursor position (like Claude Code, htop, and other ncurses apps) work correctly inside the embedded terminal.

## Why this exists

`textual-terminal` 0.3.0 has two problems that prevent TUI apps from running inside it:

1. **No DSR support.** When a program sends `ESC[6n` (cursor position request), pyte's `Screen.report_device_status()` calls `write_process_input()` — which is a [documented no-op](https://github.com/selectel/pyte/blob/master/pyte/screens.py#L1053). The program never gets a response and hangs or crashes. textual-term subclasses `pyte.Screen` and overrides that one method to write responses back to the PTY.

2. **Stripped environment.** textual-terminal clears the child process environment, breaking PATH, SHELL, USER, SSH_AUTH_SOCK, and other variables that programs depend on. textual-term inherits the full parent environment with `TERM=xterm-256color`.

## Requirements

- Python >= 3.12
- macOS / Linux (uses `pty.openpty` and `os.fork`)

## Installation

```bash
pip install textual-term
```

Or from source:

```bash
git clone https://github.com/mahrens917/textual-term.git
cd textual-term
pip install -e .
```

## Usage

```python
from textual.app import App, ComposeResult
from textual_term import Terminal


class TerminalApp(App):
    def compose(self) -> ComposeResult:
        yield Terminal(command="/bin/bash", id="term")

    def on_mount(self) -> None:
        self.query_one("#term", Terminal).start()


if __name__ == "__main__":
    TerminalApp().run()
```

### API

**`Terminal(command, *, name=None, id=None, classes=None)`**

A focusable Textual widget that runs `command` in a PTY.

- **`start()`** — Fork the PTY, start async reader/writer loops, begin 30fps rendering.
- **`stop()`** — Cancel tasks, close the PTY fd, SIGTERM the child, reap the zombie.
- **`on_key(event)`** — Translates Textual key events to ANSI sequences and writes them to the PTY. Calls `prevent_default()` and `stop()` on the event so keys don't bubble up while the terminal is focused.
- **`on_resize(event)`** — Sends `TIOCSWINSZ` to the PTY when the widget size changes.

### Subclassing

```python
from textual_term import Terminal


class MyTerminal(Terminal):
    """Terminal that releases focus on Escape."""

    DEFAULT_CSS = """
    MyTerminal { height: 1fr; border: solid #333333; }
    MyTerminal:focus { border: solid #00aa00; }
    """

    async def on_key(self, event):
        if event.key == "escape":
            self.app.set_focus(None)
            event.stop()
            event.prevent_default()
            return
        await super().on_key(event)
```

## Architecture

| Module | Description |
|--------|-------------|
| `_widget.py` | `Terminal` Textual widget — start/stop lifecycle, 30fps batched rendering |
| `_screen.py` | `ResponsiveScreen(pyte.Screen)` — overrides `write_process_input()` for DSR |
| `_emulator.py` | `PtyEmulator` — async reader/writer loops over PTY fd |
| `_pty.py` | Low-level PTY ops — fork, exec, resize, cleanup |
| `_renderer.py` | Converts pyte screen buffer to Rich `Text` lines |
| `_keys.py` | Translates Textual key names to ANSI escape sequences |

### How DSR works

```
Child process sends ESC[6n
    -> pyte Stream parses it
    -> pyte Screen.report_device_status(6)
    -> Screen.write_process_input(ESC[row;colR)
    -> ResponsiveScreen overrides this to call PtyEmulator.write_to_pty()
    -> Response written to PTY fd
    -> Child process reads cursor position
```

## Development

```bash
make check    # Full CI pipeline: format, lint, type-check, test
```

## License

MIT
