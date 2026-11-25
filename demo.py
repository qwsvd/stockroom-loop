"""Run from the checkout with Python 3.11 or newer."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from agent import run
from stockroom import Stockroom


def prompt(goal, history):
    return goal + "\nPublic trajectory:\n" + history


def stdio(goal, history):
    print(prompt(goal, history), file=sys.stderr, flush=True)
    return input()


def codex(goal, history):
    cli = shutil.which("codex.cmd" if os.name == "nt" else "codex")
    if not cli:
        raise OSError("Codex CLI missing")
    env = {k: v for k, v in os.environ.items() if k.upper() not in
           {"OPENAI_API_KEY", "CODEX_API_KEY"}}
    with tempfile.TemporaryDirectory() as tmp:
        args = [cli, "exec", "--ephemeral", "--skip-git-repo-check", "--ignore-user-config",
                "--sandbox", "read-only", "-c", 'web_search="disabled"']
        for feature in ("shell_tool", "apps", "plugins", "multi_agent"):
            args.extend(["--disable", feature])
        args.extend(["--output-last-message", "action.txt", "-"])
        try:
            result = subprocess.run(args, cwd=tmp, input=prompt(goal, history),
                                    encoding="utf-8", stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, timeout=120, env=env)
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError("Codex invocation timed out") from exc
        if result.returncode:
            raise RuntimeError("Codex exited unsuccessfully")
        with (Path(tmp) / "action.txt").open(encoding="utf-8") as stream:
            return stream.read(1025)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, choices=["stdio", "codex"])
    parser.add_argument("--steps", type=int, default=9, choices=range(1, 13))
    parser.add_argument("--steady", action="store_true", help="omit the competing sale")
    args = parser.parse_args()
    if args.policy == "codex":
        cli = shutil.which("codex.cmd" if os.name == "nt" else "codex")
        if not cli:
            parser.error("Codex CLI is required for this policy")
        login = subprocess.run([cli, "login", "status"], capture_output=True, timeout=15)
        if login.returncode or b"Logged in using ChatGPT" not in login.stderr + login.stdout:
            parser.error("This adapter requires an existing ChatGPT login")
    room = Stockroom(race=not args.steady)
    try:
        result = run(room, codex if args.policy == "codex" else stdio, args.steps)
    finally:
        room.db.close()
    print(json.dumps({"policy": args.policy, "scenario": "steady" if args.steady else "race",
                      "step_limit": args.steps, **result}, indent=2))
    return 0 if result["status"] == "verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())

