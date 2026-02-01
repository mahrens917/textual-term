# textual_term

Terminal emulator widget package for Textual.

## Modules

- `_widget.py` — `Terminal` widget class (Textual Widget)
- `_emulator.py` — `PtyEmulator` async PTY subprocess manager
- `_pty.py` — Low-level PTY operations (fork, exec, resize, cleanup)
- `_screen.py` — `ResponsiveScreen` pyte Screen subclass with DSR support
- `_renderer.py` — pyte buffer to Rich Text rendering
- `_keys.py` — Textual key event to ANSI escape sequence translation
