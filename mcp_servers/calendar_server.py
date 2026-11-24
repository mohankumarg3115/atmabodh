"""MCP server for the calendar (upcoming important events).

Run:  python mcp_servers/calendar_server.py   (stdio transport)
"""
from _common import Server, gated
from atmabodh.tools import calendar

mcp = Server("atmabodh-calendar")


@mcp.tool()
def get_next_important_event(within_hours: float = 14) -> dict:
    """The user's next important calendar event (e.g. an exam) within the
    given number of hours, or a note that there is none."""
    result = gated("calendar", calendar.get_next_important_event, "MCP: next event requested",
                   within_h=within_hours)
    return result or {"event": None}


if __name__ == "__main__":
    mcp.run()
