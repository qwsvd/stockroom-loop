"""Run the frozen exploratory sample once. Only synthetic observations leave the process."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from threading import Timer

from study import PROMPT, generate, trial

LIMIT = re.compile(r"quota|rate[ _-]?limit|usage[ _-]?limit|too many requests|payment|purchase|out of credits|buy credits|billing|(?:HTTP|status|error)\D{0,10}(?:429|402)\b|limit.{0,30}(remaining|reached)|\d+%.{0,15}(left|remaining)", re.I)
TOKEN_KEYS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")


class UsageStop(RuntimeError):
    pass


def native_cli():
    if os.name != "nt":
        return shutil.which("codex")
    native = shutil.which("codex.exe")
    if native:
        return native
    shim = shutil.which("codex.cmd")
    if shim:
        matches = list(Path(shim).parent.glob("node_modules/@openai/codex/node_modules/@openai/codex-win32-*/vendor/*/bin/codex.exe"))
        if len(matches) == 1:
            return str(matches[0])
    return None


class Client:
    def __init__(self, cli, env):
        self.cli, self.env = cli, env
        self.calls = []

    def __call__(self, order, history):
        return self.request(PROMPT + "\n" + json.dumps({"order": order, "history": history}))

    def request(self, message, limit=1024):
        entry = {"usage": None, "model": None}
        self.calls.append(entry)
        with tempfile.TemporaryDirectory() as tmp:
            args = [self.cli, "exec", "--json", "--ephemeral", "--ignore-user-config",
                    "--skip-git-repo-check", "--sandbox", "read-only", "-c", 'web_search="disabled"']
            for feature in ("apps", "plugins", "shell_tool", "multi_agent"):
                args.extend(["--disable", feature])
            args.extend(["--output-last-message", "reply.txt", "-"])
            with subprocess.Popen(args, cwd=tmp, env=self.env, stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as proc:
                timer = Timer(120, proc.kill)
                timer.start()
                try:
                    proc.stdin.write(message.encode())
                    proc.stdin.close()
                    for raw in proc.stdout:
                        line = raw.decode("utf-8", errors="replace")
                        if LIMIT.search(line):
                            proc.kill()
                            raise UsageStop("provider budget signal")
                        try:
                            event = json.loads(line)
                        except ValueError:
                            continue
                        if isinstance(event, dict) and event.get("type") in ("error", "turn.failed"):
                            proc.kill()
                            raise RuntimeError("provider error event")
                        if isinstance(event, dict) and event.get("type") == "turn.completed":
                            usage = event.get("usage") or {}
                            counts = {k: usage[k] for k in TOKEN_KEYS if type(usage.get(k)) is int}
                            entry["usage"] = counts if any(counts.values()) else None
                    if proc.wait() != 0:
                        raise RuntimeError("provider exit or timeout")
                finally:
                    timer.cancel()
            with (Path(tmp) / "reply.txt").open(encoding="utf-8") as stream:
                reply = stream.read(limit + 1)
            entry["reply"] = reply
            try:
                return json.loads(reply) if len(reply) <= limit else None
            except (ValueError, RecursionError):
                return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new file; existing campaign files are protected")
    args = parser.parse_args()
    cli = native_cli()
    if not cli:
        parser.error("native Codex CLI executable required")
    env = {k:v for k,v in os.environ.items() if k.upper() not in ("OPENAI_API_KEY","CODEX_API_KEY")}
    login = subprocess.run([cli, "login", "status"], env=env, capture_output=True, timeout=15)
    if login.returncode or b"Logged in using ChatGPT" not in login.stdout + login.stderr:
        parser.error("existing ChatGPT login required")
    version = subprocess.check_output([cli, "--version"], env=env, text=True).strip()
    with args.output.open("x", encoding="utf-8") as out:
        for seed in (10000, 10001, 10002):
            policy = Client(cli, env)
            record = trial(generate(seed), "codex", policy)
            record.update(calls=policy.calls, cli=version)
            if all(call["usage"] is not None for call in policy.calls):
                record["usage"] = {k: sum(c["usage"].get(k, 0) for c in policy.calls)
                                   for k in set.union(*(set(c["usage"]) for c in policy.calls))}
            print(json.dumps(record), file=out, flush=True)
            print(seed, record["status"], record["steps"], flush=True)
            if record["status"] == "provider_error":
                break


if __name__ == "__main__":
    main()
