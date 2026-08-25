import json
import glob

report_files = sorted(glob.glob("report_*.json"))
latest_report = report_files[-1]

with open(latest_report) as f:
    data = json.load(f)

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

tier_labels = {"correct": "CORRECT", "flagged": "FLAGGED (crashed, but validated)", "worst": "WORST (silent/wrong)"}
tier_class = {"correct": "ok", "flagged": "flagged", "worst": "crashed"}

html = """
<html>
<head>
<style>
  body { font-family: -apple-system, sans-serif; margin: 40px; background: #f5f5f5; }
  h1 { color: #222; }
  table { border-collapse: collapse; width: 100%; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 24px; }
  th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid #eee; }
  th { background: #333; color: white; }
  .ok { color: #2e7d32; font-weight: bold; }
  .flagged { color: #ef6c00; font-weight: bold; }
  .crashed { color: #c62828; font-weight: bold; }
  .rank1 { background: #e8f5e9; }
</style>
</head>
<body>
<h1>MCP Server Reliability Leaderboard</h1>
<table>
<tr><th>Rank</th><th>Server</th><th>Score</th><th>Points</th></tr>
"""

for i, (label, good, total) in enumerate(data["leaderboard"], 1):
    pct = round((good/total)*100) if total else 0
    row_class = "rank1" if i == 1 else ""
    html += f'<tr class="{row_class}"><td>{i}</td><td>{label}</td><td>{pct}%</td><td>{good}/{total}</td></tr>\n'

html += "</table><h2>Detailed Results</h2>"

for server in data["servers"]:
    html += f"<h3>{server['label']}</h3><table>"
    html += "<tr><th>Test</th><th>Input</th><th>Result</th><th>Preview</th></tr>"
    if "connection_failed" in server:
        html += f"<tr><td colspan='4' class='crashed'>Could not connect: {server['connection_failed']}</td></tr>"
    else:
        for r in server["results"]:
            tier = classify_result(r)
            preview = r["content_preview"][:80] if r["content_preview"] else ""
            html += f"<tr><td>{r['name']}</td><td>{r['input_type']}</td><td class='{tier_class[tier]}'>{tier_labels[tier]}</td><td>{preview}</td></tr>"
    html += "</table>"

html += "</body></html>"

with open("report.html", "w") as f:
    f.write(html)

print("Report saved to report.html — open it in your browser")