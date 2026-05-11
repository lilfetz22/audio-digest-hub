"""Smoke test for the MCP server — verifies the full JSON-RPC handshake.

The MCP protocol requires an ``initialize`` → ``initialized`` handshake before
any tool calls, so piping a bare ``tools/list`` message directly to the server
will always fail with "Received request before initialization was complete".

This script drives the server subprocess through the proper sequence:
  1. Send ``initialize``
  2. Send ``notifications/initialized``
  3. Send ``tools/list``
  4. Print the tool names from the response

Run from the research_papers/ directory:
    python tests/smoke_test_mcp_server.py
"""

import json
import subprocess
import sys


def send(proc, message: dict) -> None:
    line = json.dumps(message) + "\n"
    proc.stdin.write(line)
    proc.stdin.flush()


def recv(proc) -> dict | None:
    line = proc.stdout.readline()
    if not line:
        return None
    return json.loads(line)


def main() -> int:
    cmd = [sys.executable, "-m", "wiki_engine.mcp_server"]
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    try:
        # Step 1: initialize
        send(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "smoke-test", "version": "0.1"},
            },
        })
        init_response = recv(proc)
        if init_response is None or "error" in init_response:
            print(f"FAIL — initialize error: {init_response}", file=sys.stderr)
            return 1

        # Step 2: notify that client is initialized (no response expected)
        send(proc, {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        })

        # Step 3: list tools
        send(proc, {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        })
        tools_response = recv(proc)
        if tools_response is None or "error" in tools_response:
            print(f"FAIL — tools/list error: {tools_response}", file=sys.stderr)
            return 1

        tools = tools_response.get("result", {}).get("tools", [])
        print(f"OK — server returned {len(tools)} tool(s):")
        for t in tools:
            print(f"  • {t['name']}")
        return 0

    finally:
        proc.stdin.close()
        proc.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
