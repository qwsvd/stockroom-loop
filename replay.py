"""Check the published live traces against a fresh environment, offline."""
import json
from pathlib import Path
from agent import run
from stockroom import Stockroom


def check(path):
    trace = json.loads(path.read_text(encoding="utf-8-sig"))
    actions = iter(event["action"] for event in trace["history"])
    room = Stockroom(trace["scenario"] == "race")
    try:
        result = run(room, lambda *_: json.dumps(next(actions)), trace["step_limit"])
    finally:
        room.db.close()
    for key, value in result.items():
        if json.loads(json.dumps(value)) != trace[key]:
            raise ValueError(f"{path.name}: replay mismatch at {key}")
    print(f"{path.name}: {result['status']}, {len(result['history'])} decisions")


if __name__ == "__main__":
    for name in ("live-short.json", "live-race-original.json", "live-race.json"):
        check(Path(__file__).parent / "evidence" / name)
