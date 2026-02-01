"""Low-level PTY operations: fork, exec, resize, write, cleanup."""

from __future__ import annotations

import contextlib
import fcntl
import os
import pty
import signal
import struct
import termios


def open_pty(command: str, rows: int, cols: int) -> tuple[int, int]:
    """Fork a PTY and exec the command in the child. Returns (child_pid, master_fd)."""
    master_fd, slave_fd = pty.openpty()
    resize_fd(master_fd, rows, cols)
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    child_pid = os.fork()
    if child_pid == 0:
        _exec_child(master_fd, slave_fd, command, env)
    os.close(slave_fd)
    return child_pid, master_fd


_STDIO_FD_COUNT = 3


def _exec_child(master_fd: int, slave_fd: int, command: str, env: dict[str, str]) -> None:
    """Child process: set up stdio and exec the shell (never returns)."""
    os.close(master_fd)
    os.setsid()
    for i in range(_STDIO_FD_COUNT):
        os.dup2(slave_fd, i)
    if slave_fd >= _STDIO_FD_COUNT:
        os.close(slave_fd)
    os.execvpe(command, [command], env)


def resize_fd(fd: int, rows: int, cols: int) -> None:
    """Send TIOCSWINSZ ioctl to resize the PTY."""
    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


def write_to_fd(fd: int, data: str) -> None:
    """Write a UTF-8 encoded string to a file descriptor."""
    os.write(fd, data.encode("utf-8"))


def close_pty(fd: int | None, pid: int | None) -> None:
    """Close the PTY fd and reap the child process."""
    if fd is not None:
        with contextlib.suppress(OSError):
            os.close(fd)
    if pid is not None:
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, signal.SIGTERM)
        with contextlib.suppress(ChildProcessError):
            os.waitpid(pid, os.WNOHANG)
