"""MCP server for phone usage (which app is open, late-night screen time).

Run:  python mcp_servers/usage_server.py      (stdio transport)
"""
from _common import Server, gated
from atmabodh.tools import usage

mcp = Server("atmabodh-usage")


@mcp.tool()
def get_current_session() -> dict:
    """Which app is open right now, its category, minutes in this session,
    and screen minutes after 11 PM tonight. Never reads screen content."""
    return gated("usage", usage.get_current_session, "MCP: current session requested")


if __name__ == "__main__":
    mcp.run()
