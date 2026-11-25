"""Bounded decision loop. A policy receives only goal and public history."""
import json
from stockroom import GOAL, verified


def run(room, policy, limit=9):
    if type(limit) is not int or not 1 <= limit <= 12:
        raise ValueError("step limit must be between 1 and 12")
    history = []
    status = "step_limit"
    for _ in range(limit):
        try:
            raw = policy(GOAL, json.dumps(history, ensure_ascii=True))
        except (OSError, TimeoutError, RuntimeError, EOFError) as exc:
            status = "provider_error"
            history.append({"error": type(exc).__name__})
            break
        try:
            if not isinstance(raw, str) or len(raw) > 1024:
                raise ValueError()
            action = json.loads(raw)
        except (ValueError, RecursionError):
            history.append({"observation": {"error": "expected one short JSON action"}})
            continue
        if action == {"op": "finish"}:
            status = "verified" if verified(room) else "wrong_state"
            history.append({"action": action, "observation": status})
            break
        observation = room.act(action)
        history.append({"action": action, "observation": observation})
    return {"status": status, "history": history, "external_sale": room.sold,
            "final_lots": room.snapshot()}
