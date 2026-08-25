import asyncio
from fastmcp import Client
import json
from datetime import datetime

SERVERS = [
    {
        "label": "DuckDuckGo Search",
        "config": {"mcpServers": {"duckduckgo": {"command": "uvx", "args": ["duckduckgo-mcp-server"]}}},
        "tests": [
            {"name": "Normal call", "tool": "search", "args": {"query": "MCP protocol"}, "input_type": "valid"},
            {"name": "Empty input", "tool": "search", "args": {"query": ""}, "input_type": "invalid"},
            {"name": "Garbage input", "tool": "search", "args": {"query": "asdkjaslkdjaslkdjalskdj123123"}, "input_type": "invalid"},
        ],
    },
    {
        "label": "Fetch (web page reader)",
        "config": {"mcpServers": {"fetch": {"command": "uvx", "args": ["mcp-server-fetch"]}}},
        "tests": [
            {"name": "Normal call", "tool": "fetch", "args": {"url": "https://example.com"}, "input_type": "valid"},
            {"name": "Empty input", "tool": "fetch", "args": {"url": ""}, "input_type": "invalid"},
            {"name": "Garbage input", "tool": "fetch", "args": {"url": "not-a-real-url-at-all"}, "input_type": "invalid"},
        ],
    },
    {
        "label": "Everything (MCP reference test server)",
        "config": {"mcpServers": {"everything": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-everything"]}}},
        "tests": [
            {"name": "Normal call", "tool": "echo", "args": {"message": "hello"}, "input_type": "valid"},
            {"name": "Empty input", "tool": "echo", "args": {"message": ""}, "input_type": "invalid"},
            {"name": "Wrong type", "tool": "echo", "args": {"message": 12345}, "input_type": "invalid"},
        ],
    },
    {
        "label": "Time",
        "config": {"mcpServers": {"time": {"command": "uvx", "args": ["mcp-server-time"]}}},
        "tests": [
            {"name": "Normal call", "tool": "get_current_time", "args": {"timezone": "Asia/Kolkata"}, "input_type": "valid"},
            {"name": "Invalid timezone", "tool": "get_current_time", "args": {"timezone": "Not/ARealZone"}, "input_type": "invalid"},
            {"name": "Empty input", "tool": "get_current_time", "args": {"timezone": ""}, "input_type": "invalid"},
        ],
    },
    {
        "label": "Filesystem",
        "config": {"mcpServers": {"filesystem": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]}}},
        "tests": [
            {"name": "Normal call", "tool": "list_directory", "args": {"path": "/tmp"}, "input_type": "valid"},
            {"name": "Nonexistent path", "tool": "list_directory", "args": {"path": "/tmp/this_folder_does_not_exist_xyz"}, "input_type": "invalid"},
            {"name": "Empty input", "tool": "list_directory", "args": {"path": ""}, "input_type": "invalid"},
        ],
    },
    {
        "label": "Memory",
        "config": {"mcpServers": {"memory": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"]}}},
        "tests": [
            {"name": "Normal call", "tool": "create_entities", "args": {"entities": [{"name": "Test", "entityType": "person", "observations": ["likes testing"]}]}, "input_type": "valid"},
            {"name": "Empty input", "tool": "create_entities", "args": {"entities": []}, "input_type": "invalid"},
            {"name": "Wrong type", "tool": "create_entities", "args": {"entities": "not_a_list"}, "input_type": "invalid"},
        ],
    },
]

async def run_single_test(client, test):
    result_info = {"name": test["name"], "input_type": test["input_type"], "crashed": False, "is_error": None, "content_preview": None}
    try:
        result = await client.call_tool(test["tool"], test["args"])
        result_info["is_error"] = result.is_error
        preview_source = result.data if result.data is not None else result.content
        result_info["content_preview"] = str(preview_source)[:150]
    except Exception as e:
        result_info["crashed"] = True
        result_info["content_preview"] = str(e)[:150]
    return result_info

async def run_eval_suite(server):
    client = Client(server["config"])
    results = []
    try:
        async with client:
            for test in server["tests"]:
                results.append(await run_single_test(client, test))
    except Exception as e:
        return {"label": server["label"], "connection_failed": str(e)[:150]}
    return {"label": server["label"], "results": results}

def classify_result(r):
    if r["input_type"] == "invalid":
        if r["is_error"] is True:
            return "correct"
        elif r["crashed"]:
            return "flagged"
        else:
            return "worst"
    else:
        if r["crashed"]:
            return "worst"
        elif r["is_error"] is True:
            return "worst"
        else:
            return "correct"

def calculate_score(server_report):
    if "connection_failed" in server_report:
        return 0, 0
    tier_points = {"correct": 2, "flagged": 1, "worst": 0}
    total_possible = len(server_report["results"]) * 2
    earned = sum(tier_points[classify_result(r)] for r in server_report["results"])
    return earned, total_possible

async def main():
    all_reports = await asyncio.gather(*[run_eval_suite(s) for s in SERVERS])

    print("\n" + "="*60)
    print("MULTI-SERVER RELIABILITY REPORT")
    print("="*60)

    scored = []
    for report in all_reports:
        print(f"\n### {report['label']} ###")
        if "connection_failed" in report:
            print(f"  COULD NOT CONNECT: {report['connection_failed']}")
            scored.append((report["label"], 0, 0))
            continue
        for r in report["results"]:
            status = "CRASHED" if r["crashed"] else "OK"
            print(f"  [{status}] {r['name']} ({r['input_type']}) — is_error={r['is_error']} — tier={classify_result(r)}")
            if r["crashed"]:
                print(f"      reason: {r['content_preview']}")
        good, total = calculate_score(report)
        scored.append((report["label"], good, total))

    print("\n" + "="*60)
    print("RELIABILITY LEADERBOARD")
    print("="*60)
    scored.sort(key=lambda x: (x[1]/x[2] if x[2] else 0), reverse=True)
    for rank, (label, good, total) in enumerate(scored, 1):
        pct = round((good/total)*100) if total else 0
        print(f"{rank}. {label:<35} {pct}% ({good}/{total})")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"report_{timestamp}.json"
    with open(filename, "w") as f:
        json.dump({"servers": all_reports, "leaderboard": scored}, f, indent=2)
    print(f"\nSaved full report to {filename}")

asyncio.run(main())