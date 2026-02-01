# textual-term

Terminal emulator widget for [Textual](https://github.com/Textualize/textual). Embeds an interactive PTY terminal inside Textual applications with DSR (Device Status Report) support, enabling TUI apps like Claude Code to run inside the embedded terminal.

## Installation

```bash
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

## Key Features

- DSR support via pyte `write_process_input` override, enabling cursor-position-dependent TUI apps
- Full parent environment inheritance (PATH, SHELL, SSH_AUTH_SOCK preserved)
- Batched rendering at 30fps (avoids per-read refresh storms)
- Clean PTY shutdown (fd close, SIGTERM, waitpid)

## Development

```bash
make check
```
