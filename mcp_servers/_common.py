"""Shared helpers for the three MCP servers.

Each data source is its own MCP server, so the user can switch one off
without touching the others. Every tool goes through the Privacy Gate,
so MCP access is consent-checked and logged like everything else.

Works with the MCP Python SDK v2 (MCPServer) and v1 (FastMCP).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so `atmabodh` imports work

try:                                   # MCP Python SDK 2.x
    from mcp.server.mcpserver import MCPServer as Server
except ImportError:                    # MCP Python SDK 1.x
    from mcp.server.fastmcp import FastMCP as Server

from atmabodh.gate import PrivacyGate  # noqa: E402

gate = PrivacyGate()


def gated(source: str, fn, reason: str, **kwargs):
    result = gate.call(source, fn, reason, **kwargs)
    if result is None and not gate.consent()[source]:
        return {"error": f"The user has switched off '{source}' data for AtmaBodh."}
    return result
