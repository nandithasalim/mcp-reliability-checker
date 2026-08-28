# MCP Reliability Checker

An automated testing framework for Model Context Protocol (MCP) servers. Connects to any MCP server, runs a standardized suite of edge-case tests (empty input, malformed types, invalid arguments), and reports how gracefully — or ungracefully — the server handles them.

## Why

MCP servers are proliferating fast (2,000+ in the official registry as of early 2026), but there's no standard way to know if one is reliable before connecting it to your own AI setup. This tool programmatically stress-tests any MCP server and surfaces real reliability gaps — not just "does it work," but "does it fail honestly when it should."

## Results (real run, not hypothetical)

Tested 14 public MCP servers — official reference servers (Everything, Filesystem, Memory, Sequential Thinking, Git, SQLite) and community/third-party servers (DuckDuckGo Search, Fetch, Time, Wikipedia, Arxiv, Puppeteer, Context7, MediaWiki) — across 33 total edge-case tests.

**Headline finding: no server scored above 67% reliability. Average score across all servers: ~53%.**

Two distinct failure patterns emerged:
- **Silent failure:** servers (e.g. DuckDuckGo Search) that return `is_error=False` even on invalid input — failures are only visible in natural-language text, not in a machine-checkable flag.
- **Uncaught crashes:** servers (e.g. Fetch, Time, Everything) that correctly reject bad input but do so by raising a raw exception instead of returning MCP's structured error response — meaning every caller must wrap every tool call in try/except rather than trusting `is_error`.

**Bonus finding:** 3 of 14 servers (SQLite, MediaWiki, Wikipedia) failed to even start, due to outdated dependencies incompatible with the current MCP SDK — e.g. `mcp-server-sqlite` calls a `list_resources()` method that no longer exists on the current `Server` class, and `mediawiki-mcp-server` imports `FastMCP` from a module path that was renamed to `MCPServer` in MCP SDK v2. Both are concrete, reproducible bugs suitable for upstream bug reports.

Full results: see `report_*.json` for raw data, or open `report.html` for a formatted leaderboard.

## How it works

1. Connects to a target MCP server using FastMCP's `Client`, over `stdio` transport
2. Runs 3 tests per server: one valid call, two deliberately invalid ones (empty, malformed, or wrong-typed input)
3. Classifies each result into a 3-tier system:
   - **Correct** — succeeded on valid input, or properly returned `is_error=True` on invalid input
   - **Flagged** — invalid input correctly rejected, but via a raw exception instead of MCP's structured error mechanism
   - **Worst** — invalid input silently accepted as success, or valid input crashed/falsely flagged as an error
4. Tests all servers concurrently using `asyncio.gather`
5. Outputs a timestamped JSON report and an auto-generated HTML leaderboard

## Tech stack

Python · FastMCP (MCP client) · asyncio · JSON

## Running it

```bash
pip install fastmcp
python3 eval_runner.py       # runs the tests, saves report_<timestamp>.json
python3 generate_report.py   # builds report.html from the latest JSON
open report.html
```

Requires `uv`/`uvx` and Node.js (`npx`) installed, since tested servers are launched through those.

## Adding a new server to test

Add an entry to the `SERVERS` list in `eval_runner.py`:
```python
{
    "label": "My Server",
    "config": {"mcpServers": {"myserver": {"command": "uvx", "args": ["my-mcp-package"]}}},
    "tests": [
        {"name": "Normal call", "tool": "my_tool", "args": {...}, "input_type": "valid"},
        {"name": "Bad input", "tool": "my_tool", "args": {...}, "input_type": "invalid"},
    ],
},
```

## What's next

- Persistent tracking across runs to detect reliability regressions over time
- File upstream bug reports for the SQLite/MediaWiki failures found above
- Expand test categories: latency/timeout checks, concurrent-load testing
	
