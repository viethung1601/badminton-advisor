"""MCP server for Badminton Advisor. Tools come from the shared registry (badminton.presentation.tools).
Runs over stdio. Do NOT print() to stdout (stdout is the protocol channel)."""
import asyncio
import contextlib
import json
import sys

from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from badminton.presentation.tools import TOOLS, run_tool

server = Server("badminton-advisor")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [types.Tool(name=t.name, description=t.mcp_description, inputSchema=t.input_schema)
            for t in TOOLS]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    # a stray print() inside a tool must not corrupt the protocol stream
    with contextlib.redirect_stdout(sys.stderr):
        content, is_error = run_tool(name, arguments or {})
    if is_error:
        raise ValueError(content["error"])      # the SDK turns this into isError=True
    return [types.TextContent(type="text", text=json.dumps(content, ensure_ascii=False))]


async def main() -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())