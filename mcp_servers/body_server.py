"""MCP server for body data (sleep, heart rate, steps).

Run:  python mcp_servers/body_server.py      (stdio transport)
"""
from _common import Server, gated
from atmabodh.tools import body

mcp = Server("atmabodh-body")


@mcp.tool()
def get_sleep_summary(nights: int = 3) -> dict:
    """Summary of the user's last few nights of sleep: average hours,
    usual hours, number of late nights and total sleep debt."""
    return gated("body", body.get_sleep_summary, "MCP: sleep summary requested", nights=nights)


if __name__ == "__main__":
    mcp.run()
