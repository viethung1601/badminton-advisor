"""Shim: the MCP server lives in badminton.presentation.mcp_server."""
import asyncio

from badminton.presentation.mcp_server import main

if __name__ == "__main__":
    asyncio.run(main())