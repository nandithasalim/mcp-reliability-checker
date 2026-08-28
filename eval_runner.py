import asyncio
from fastmcp import Client
import json
from datetime import datetime

with open("servers.json") as f:
    SERVERS = json.load(f)
    
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
        if r["crashed"] or r["is_error"] is True:
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