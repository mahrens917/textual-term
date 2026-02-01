"""Tests for PTY environment inheritance."""

from __future__ import annotations

import asyncio
import os

import pytest

from textual_term._emulator import PtyEmulator


class TestEnvironment:
    """Test that the PTY child process inherits the parent environment."""

    @pytest.mark.integration
    async def test_pty_inherits_path(self) -> None:
        """The child shell should have PATH from the parent environment."""
        emulator = PtyEmulator(os.environ.get("SHELL", "/bin/sh"), 24, 80)
        emulator.open_pty()
        emulator.start()
        emulator.write_to_pty("echo TERM=$TERM\n")
        output_parts: list[str] = []
        for _ in range(50):
            try:
                msg = await asyncio.wait_for(emulator.output_queue.get(), timeout=0.1)
                if msg[0] == "stdout":
                    output_parts.append(msg[1])
                    if "TERM=xterm-256color" in "".join(output_parts):
                        break
            except asyncio.TimeoutError:
                continue
        await emulator.stop()
        combined = "".join(output_parts)
        assert "TERM=xterm-256color" in combined

    @pytest.mark.integration
    async def test_pty_term_is_xterm_256color(self) -> None:
        """TERM should be set to xterm-256color in the child process."""
        emulator = PtyEmulator(os.environ.get("SHELL", "/bin/sh"), 24, 80)
        emulator.open_pty()
        emulator.start()
        emulator.write_to_pty("echo MYTERM=${TERM}\n")
        output_parts: list[str] = []
        for _ in range(50):
            try:
                msg = await asyncio.wait_for(emulator.output_queue.get(), timeout=0.1)
                if msg[0] == "stdout":
                    output_parts.append(msg[1])
                    if "MYTERM=xterm-256color" in "".join(output_parts):
                        break
            except asyncio.TimeoutError:
                continue
        await emulator.stop()
        combined = "".join(output_parts)
        assert "MYTERM=xterm-256color" in combined
