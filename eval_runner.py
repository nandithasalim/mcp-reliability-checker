import asyncio
from fastmcp import Client

TEST_CASES = [
    {"name": "Normal call", "tool": None, "args": None, "expect_error": False},
    {"name": "Empty input", "tool": None, "args": None, "expect_error": True},
    {"name": "Garbage input", "tool": None, "args": None, "expect_error": False},
]

# Each server defines its own tool name + how to fill in the test args
SERVERS = [
    {
        "label": "DuckDuckGo Search",
        "config": {
            "mcpServers": {"duckduckgo": {"command": "uvx", "args": ["duckduckgo-mcp-server"]}}
        },
        "tool": "search",
        "arg_key": "query",
        "normal_value": "MCP protocol",
        "garbage_value": "asdkjaslkdjaslkdjalskdj123123",
    },
    {
        "label": "Fetch (web page reader)",
        "config": {
            "mcpServers": {"fetch": {"command": "uvx", "args": ["mcp-server-fetch"]}}
        },
        "tool": "fetch",
        "arg_key": "url",
        "normal_value": "https://example.com",
        "garbage_value": "not-a-real-url-at-all",
    },
]

async def run_single_test(client, tool, args):
    result_info = {"crashed": False, "is_error": None, "content_preview": None}
    try:
        result = await client.call_tool(tool, args)
        result_info["is_error"] = result.is_error
        result_info["content_preview"] = str(result.data)[:100]
    except Exception as e:
        result_info["crashed"] = True
        result_info["content_preview"] = str(e)[:300]
    return result_info

async def run_eval_suite(server):
    """Run the 3 standard tests against one server, return a report dict."""
    client = Client(server["config"])
    results = {}
    try:
        async with client:
            results["Normal call"] = await run_single_test(
                client, server["tool"], {server["arg_key"]: server["normal_value"]}
            )
            results["Empty input"] = await run_single_test(
                client, server["tool"], {server["arg_key"]: ""}
            )
            results["Garbage input"] = await run_single_test(
                client, server["tool"], {server["arg_key"]: server["garbage_value"]}
            )
    except Exception as e:
        # server failed to even connect/start
        results["connection_failed"] = str(e)[:150]

    return {"label": server["label"], "results": results}

async def main():
    # KEY PART: fire all servers' test suites AT THE SAME TIME, not one by one
    all_reports = await asyncio.gather(*[run_eval_suite(s) for s in SERVERS])

    print("\n" + "="*60)
    print("MULTI-SERVER RELIABILITY REPORT")
    print("="*60)

    for report in all_reports:
        print(f"\n### {report['label']} ###")
        if "connection_failed" in report["results"]:
            print(f"  COULD NOT CONNECT: {report['results']['connection_failed']}")
            continue
        for test_name, r in report["results"].items():
            status = "CRASHED" if r["crashed"] else "OK"
            print(f"  [{status}] {test_name} — is_error={r['is_error']}")
            if r["crashed"]:
                print(f"      reason: {r['content_preview']}")

asyncio.run(main())