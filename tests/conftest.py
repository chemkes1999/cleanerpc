"""
Pytest configuration and shared fixtures for CleanerPC test suite.
Simulates Windows administrative and standard user environments on cross-platform runners.
"""

from __future__ import annotations

import os
import sys
import subprocess

# Asegurar que el directorio raíz del proyecto esté en sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import cleaner


class DummyStartupInfo:
    def __init__(self):
        self.dwFlags = 0


@pytest.fixture
def mock_win32_admin(monkeypatch):
    """Simulates a Windows environment with Administrative privileges."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(cleaner, "is_admin", lambda: True)
    if not hasattr(subprocess, "STARTUPINFO"):
        monkeypatch.setattr(subprocess, "STARTUPINFO", DummyStartupInfo, raising=False)
    if not hasattr(subprocess, "STARTF_USESHOWWINDOW"):
        monkeypatch.setattr(subprocess, "STARTF_USESHOWWINDOW", 1, raising=False)


@pytest.fixture
def mock_win32_nonadmin(monkeypatch):
    """Simulates a Windows environment without Administrative privileges."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(cleaner, "is_admin", lambda: False)
    if not hasattr(subprocess, "STARTUPINFO"):
        monkeypatch.setattr(subprocess, "STARTUPINFO", DummyStartupInfo, raising=False)
    if not hasattr(subprocess, "STARTF_USESHOWWINDOW"):
        monkeypatch.setattr(subprocess, "STARTF_USESHOWWINDOW", 1, raising=False)
