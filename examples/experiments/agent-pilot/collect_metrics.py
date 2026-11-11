"""Collect completed pilot session metadata; never poll running trials."""

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode


def get(path):
    return json.loads(subprocess.check_output(["opencode", "api", "get", path], text=True))


def collect(session):
    info = get(f"/api/session/{session}")["data"]
    if info.get("outcome") != "succeeded":
        raise RuntimeError("Collect only after the trial completion notification")
    messages = []
    query = {"limit": "100", "order": "asc"}
    while True:
        page = get(f"/api/session/{session}/message?" + urlencode(query))
        messages.extend(page["data"])
        cursor = page.get("cursor", {}).get("next")
        if not cursor:
            break
        query = {"limit": "100", "cursor": cursor}
    calls = Counter()
    failures = Counter()
    commands = []
    for message in messages:
        if message["type"] != "assistant":
            continue
        for part in message.get("content", []):
            if part.get("type") != "tool":
                continue
            calls[part["name"]] += 1
            state = part["state"]
            if state["status"] == "error":
                failures[part["name"]] += 1
            command = state.get("input", {}).get("command")
            if command:
                commands.append(command)
    return {
        "session_id": session,
        "model": info.get("model"),
        "outcome": info["outcome"],
        "time": info["time"],
        "session_wall_seconds": (info["time"]["idle"] - info["time"]["created"]) / 1000,
        "tokens_reported_by_harness": info["tokens"],
        "cost_reported_by_harness": info["cost"],
        "actual_cost_usd": None,
        "cost_note": "Harness model pricing was unavailable; zero is not evidence of free usage.",
        "assistant_messages": sum(m["type"] == "assistant" for m in messages),
        "tool_calls": dict(calls),
        "tool_errors": dict(failures),
        "shell_commands_for_audit": commands,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("session")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = collect(args.session)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "shell_commands_for_audit"}))
