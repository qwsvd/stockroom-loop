"""Print policy metrics and independently reapply the published live decisions."""
from collections import Counter
import gzip
import json
from statistics import mean
from evaluate import ROOT, compare
from study import generate, trial


def summarize(name, rows):
    success = [r for r in rows if r["success"]]
    return dict(policy=name, n=len(rows), success_rate=len(success)/len(rows),
                failure_rate=(len(rows)-len(success))/len(rows), status=dict(Counter(r["status"] for r in rows)),
                mean_completion_steps=mean(r["steps"] for r in success) if success else None,
                seconds=sum(r["elapsed_s"] for r in rows),
                **{k:sum(r[k] for r in rows) for k in
                   ("steps","model_decisions","tools","illegal","errors","rejected","recovered")})


def check_live(row):
    calls = iter(row["calls"])
    def replay(*_):
        call = next(calls)
        if "reply" not in call:
            # Replay a recorded transport stop without contacting the service.
            from live_study import UsageStop
            kind = row["history"][-1]["observation"]["provider_error"]
            raise {"UsageStop":UsageStop, "RuntimeError":RuntimeError, "OSError":OSError,
                   "TimeoutError":TimeoutError, "FileNotFoundError":FileNotFoundError}[kind]()
        try:
            return json.loads(call["reply"]) if len(call["reply"])<=1024 else None
        except (ValueError, RecursionError):
            return None
    compare(row, trial(generate(row["seed"]), "codex", replay))
    if next(calls, None) is not None:
        raise ValueError("extra live decision")
    metered = [call["usage"] for call in row["calls"]]
    total = None
    if all(usage is not None for usage in metered):
        keys = {key for usage in metered for key in usage}
        total = {key: sum(usage.get(key, 0) for usage in metered) for key in keys}
    if row["usage"] != total:
        raise ValueError("task usage differs from per-decision evidence")


if __name__ == "__main__":
    for split in ("dev","holdout"):
        with gzip.open(ROOT / (split+".jsonl.gz"), "rt", encoding="utf-8") as stream:
            rows = list(map(json.loads, stream))
        for policy in ("fixed","adaptive"):
            print(split, json.dumps(summarize(policy, [r for r in rows if r["policy"]==policy])))
    rows = list(map(json.loads,(ROOT/"live.jsonl").read_text(encoding="utf-8").splitlines()))
    seeds = [row["seed"] for row in rows]
    if not seeds or seeds != [10000, 10001, 10002][:len(rows)]:
        raise ValueError("unexpected or missing live seeds")
    if any(r["status"] == "provider_error" for r in rows[:-1]):
        raise ValueError("continued after provider stop")
    if len(rows) < 3 and rows[-1]["status"] != "provider_error":
        raise ValueError("incomplete campaign")
    for row in rows:
        check_live(row)
    print("live", json.dumps(summarize("codex", rows)))
