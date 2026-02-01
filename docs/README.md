# textual-term Documentation

## Architecture

The widget is composed of four internal modules:

- `_screen.py` — `ResponsiveScreen(pyte.Screen)` subclass that writes DSR responses back to the PTY fd
- `_emulator.py` — `PtyEmulator` manages the child process via `pty.fork()` with async I/O queues
- `_renderer.py` — converts pyte screen buffer to Rich Text lines for display
- `_keys.py` — translates Textual key events to ANSI escape sequences

## DSR (Device Status Report)

When a child process sends `ESC[6n` (cursor position request), pyte's `Screen.report_device_status()` calls `write_process_input()` with the response. The base pyte implementation is a no-op. `ResponsiveScreen` overrides this to write the response back to the PTY fd, so the child process receives the cursor position it asked for.

## Environment

The PTY child process inherits the full parent environment with `TERM=xterm-256color` set. This preserves PATH, SHELL, USER, SSH_AUTH_SOCK, and other variables that programs depend on.
