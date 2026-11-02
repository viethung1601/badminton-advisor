"""Chụp danh sách tool của agent và MCP server HIỆN TẠI (trước khi gộp vào registry).
Chạy từ thư mục gốc: python tests/make_tools_baseline.py"""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "tests" / "golden"

import agent  # noqa: E402  (cần ANTHROPIC_API_KEY trong .env như bình thường)

(OUT / "agent_tools.json").write_text(
    json.dumps(agent.TOOLS, ensure_ascii=False, indent=1), encoding="utf-8")

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402


async def main():
    params = StdioServerParameters(
        command=sys.executable, args=[str(ROOT / "src" / "mcp_server.py")])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = (await s.list_tools()).tools
            data = [{"name": t.name, "description": t.description,
                     "properties": sorted(t.inputSchema.get("properties", {})),
                     "required": sorted(t.inputSchema.get("required", []))} for t in tools]
            (OUT / "mcp_tools.json").write_text(
                json.dumps(sorted(data, key=lambda x: x["name"]), ensure_ascii=False, indent=1),
                encoding="utf-8")

asyncio.run(main())
print("saved agent_tools.json and mcp_tools.json")
