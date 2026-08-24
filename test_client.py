import asyncio
from fastmcp import Client

async def run_test(client, test_name, tool_name, args):
    """Run one test case and report pass/fail cleanly, including the actual content."""
    print(f"\n--- Test: {test_name} ---")
    try:
        result = await client.call_tool(tool_name, args)
        if result.is_error:
            print(f"Server returned an error (handled gracefully)")
        else:
            print(f"Server said: Success")

        # Print the actual data content, so we can see if it's genuinely useful or secretly empty/broken
        print(f"Actual content: {result.data}")
        return True
    except Exception as e:
        print(f"CRASHED — server/connection broke: {e}")
        return False

async def main():
    client = Client({
        "mcpServers": {
            "duckduckgo": {
                "command": "uvx",
                "args": ["duckduckgo-mcp-server"]
            }
        }
    })
    async with client:
        await run_test(client, "Normal search", "search", {"query": "MCP protocol"})
        await run_test(client, "Empty query", "search", {"query": ""})
        await run_test(client, "Garbage input", "search", {"query": "asdkjaslkdjaslkdjalskdj123123"})

asyncio.run(main())