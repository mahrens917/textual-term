"""Tests for the PTY emulator."""

from __future__ import annotations

import asyncio
import os

import pytest

from textual_term._emulator import PtyEmulator
from textual_term._pty import close_pty, open_pty, resize_fd


class TestPtyEmulator:
    """Test PtyEmulator lifecycle and I/O."""

    @pytest.mark.integration
    async def test_echo(self) -> None:
        """Writing to PTY should produce output on output_queue."""
        shell = os.environ.get("SHELL", "/bin/sh")
        emulator = PtyEmulator(shell, 24, 80)
        emulator.open_pty()
        emulator.start()
        emulator.write_to_pty("echo PTY_TEST_OUTPUT\n")
        output_parts: list[str] = []
        for _ in range(50):
            try:
                msg = await asyncio.wait_for(emulator.output_queue.get(), timeout=0.1)
                if msg[0] == "stdout":
                    output_parts.append(msg[1])
                    if "PTY_TEST_OUTPUT" in "".join(output_parts):
                        break
            except TimeoutError:
                continue
        await emulator.stop()
        combined = "".join(output_parts)
        assert "PTY_TEST_OUTPUT" in combined

    @pytest.mark.integration
    async def test_stop_cleans_up(self) -> None:
        """After stop(), fd and pid should be None."""
        shell = os.environ.get("SHELL", "/bin/sh")
        emulator = PtyEmulator(shell, 24, 80)
        emulator.open_pty()
        emulator.start()
        await asyncio.sleep(0.1)
        await emulator.stop()
        assert emulator._fd is None
        assert emulator._pid is None


class TestPtyFunctions:
    """Test low-level PTY functions."""

    def test_open_and_close(self) -> None:
        """open_pty should return valid pid and fd, close_pty should clean up."""
        pid, fd = open_pty("/bin/sh", 24, 80)
        assert pid > 0
        assert fd >= 0
        close_pty(fd, pid)

    def test_resize(self) -> None:
        """resize_fd should not raise for valid dimensions."""
        pid, fd = open_pty("/bin/sh", 24, 80)
        resize_fd(fd, 40, 120)
        close_pty(fd, pid)
