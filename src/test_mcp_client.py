import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = str(Path(__file__).parent / "mcp_server.py")


async def main():
    params = StdioServerParameters(command=sys.executable, args=[SERVER])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()           # tools/list
            for t in tools.tools:
                print("TOOL:", t.name, "| tham số:", list(
                    t.inputSchema.get("properties", {})))

            # tools/call
            ok = await session.call_tool("find_shoe", {"name": "Subaxia GT"})
            print("\nfind_shoe isError =", ok.isError)
            print(ok.content[0].text[:400])

            bad = await session.call_tool("recommend_shoes", {"gender": "robot", "size_eu": 42})
            print("\ngender sai isError =", bad.isError)
            print(bad.content[0].text[:300])

            rk = await session.call_tool("recommend_racket",
                                         {"level": "beginner", "play_style": "attack", "max_price": 60})
            print("\nrecommend_racket isError =", rk.isError)
            print(rk.content[0].text[:400])

            bad2 = await session.call_tool("recommend_racket",
                                           {"level": "pro", "play_style": "attack", "max_price": 60})
            print("\nlevel sai isError =", bad2.isError)

            kn = await session.call_tool("search_knowledge", {"query": "nặng đầu là gì"})
            print("\nsearch_knowledge isError =", kn.isError)
            print(kn.content[0].text[:300])
asyncio.run(main())
