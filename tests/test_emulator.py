"""Tests for the PTY emulator."""

from __future__ import annotations

import asyncio
import os

import pytest

from textual_term._emulator import PtyEmulator


class TestPtyEmulator:
    """Test PtyEmulator lifecycle and I/O."""

    @pytest.mark.integration
    async def test_echo(self) -> None:
        """Writing to PTY should produce output on output_queue."""
        emulator = PtyEmulator(os.environ.get("SHELL", "/bin/sh"), 24, 80)
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
            except asyncio.TimeoutError:
                continue
        await emulator.stop()
        combined = "".join(output_parts)
        assert "PTY_TEST_OUTPUT" in combined

    @pytest.mark.integration
    async def test_stop_cleans_up(self) -> None:
        """After stop(), fd and pid should be None."""
        emulator = PtyEmulator(os.environ.get("SHELL", "/bin/sh"), 24, 80)
        emulator.open_pty()
        emulator.start()
        await asyncio.sleep(0.1)
        await emulator.stop()
        assert emulator._fd is None
        assert emulator._pid is None

    def test_resize(self) -> None:
        """Resize should update internal rows/cols."""
        emulator = PtyEmulator("/bin/sh", 24, 80)
        emulator.open_pty()
        emulator.resize(40, 120)
        assert emulator._rows == 40
        assert emulator._cols == 120
        os.close(emulator._fd)
        try:
            os.waitpid(emulator._pid, os.WNOHANG)
        except ChildProcessError:
            pass
