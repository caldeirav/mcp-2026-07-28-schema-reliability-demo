"""Pytest path setup: import agent and mcp modules without shadowing the MCP SDK."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / "src" / "agent"
MCP_DIR = ROOT / "src" / "mcp"

for path in (AGENT_DIR, MCP_DIR):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)
