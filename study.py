"""Paired stock-allocation study. All quantities and expiry days are integers."""
import json
import random
import time
from dataclasses import dataclass


@dataclass
class Case:
    seed: int
    order: dict
    lots: dict
    sale: dict


def generate(seed):
    rng = random.Random(seed)
    sku = rng.choice(["tea", "soap", "rice", "beans"])
    day = rng.randint(1, 20)
    lots = {}
    for i in range(rng.randint(3, 8)):
        product = sku if i < 2 else rng.choice([sku, "other"])
        expiry = day + (rng.randint(0, 2) if i < 2 else rng.randint(-2, 4))
        lots[f"L{i}"] = [product, expiry, rng.randint(1, 5)]
    priority = rng.choice(["earliest", "latest"])
    order = dict(sku=sku, min_day=day, priority=priority)
    ranked = sorted((lot for lot, (p, d, _) in lots.items() if p == sku and d >= day),
                    key=lambda lot: (lots[lot][1] * (1 if priority == "earliest" else -1), lot))
    total = sum(lots[k][2] for k in ranked)
    regime = seed % 4
    order["qty"] = total + 1 if regime == 2 else rng.randint(1, total)
    sale = {}
    if regime == 1:
        sale = {k: lots[k][2] for k in ranked[:2]}
    if regime == 3:
        sale = {k: rng.randint(0, lots[k][2]) for k in lots}
    return Case(seed, order, lots, sale)


PROMPT = """Allocate exactly qty of sku with expiry day >= min_day. Follow priority
(earliest or latest expiry), breaking ties by ascending lot ID. Each lot value is
[product,expiry_day,available]. Stock can change after inspection. Return one JSON
object per decision: {"op":"inspect"}, {"op":"submit","pick":{"LOT":POSITIVE_INTEGER}},
or {"op":"shortage"} if impossible. Submit the complete allocation in one action.
Rejected submissions change no holds. You may inspect again. Nine decisions maximum."""


class Market:
    def __init__(self, case):
        self.case = case
        self.stock = {key: list(row) for key, row in case.lots.items()}
        self.held = {}
        self.observed = False

    def apply(self, action):
        if action == {"op": "inspect"}:
            snapshot = {key: row.copy() for key, row in self.stock.items()}
            if not self.observed:
                for key, lost in self.case.sale.items():
                    self.stock[key][2] -= lost
                self.observed = True
            return {"lots": snapshot}
        if action == {"op": "shortage"} and self.observed:
            return {"terminal": "shortage"}
        if not isinstance(action, dict) or set(action) != {"op", "pick"} or action["op"] != "submit":
            return {"illegal": "expected inspect, complete submit, or shortage after inspection"}
        pick = action["pick"]
        if (not self.observed or not isinstance(pick, dict) or not pick or
                any(k not in self.stock or type(v) is not int or v < 1 for k, v in pick.items())):
            return {"illegal": "inspect first; use known lots and positive integer units"}
        order = self.case.order
        if sum(pick.values()) != order["qty"]:
            return {"rejected": "wrong total"}
        for key, units in pick.items():
            sku, day, available = self.stock[key]
            if sku != order["sku"] or day < order["min_day"] or units > available:
                return {"rejected": "eligibility or availability changed; inspect"}
        for key, units in pick.items():
            self.stock[key][2] -= units
        self.held = pick.copy()
        return {"terminal": "filled"}


def grade(case, market, claim):
    """Conservation plus an exchange condition: no better eligible unit left unused."""
    if not market.observed or set(market.stock) != set(case.lots):
        return False
    if set(market.held) - set(case.lots):
        return False
    eligible = []
    for key, (sku, day, initial) in case.lots.items():
        p, d, left = market.stock[key]
        held = market.held.get(key, 0)
        if type(left) is not int or type(held) is not int:
            return False
        if (p, d) != (sku, day) or min(left, held) < 0 or left + held != initial - case.sale.get(key, 0):
            return False
        if sku == case.order["sku"] and day >= case.order["min_day"]:
            eligible.append((day if case.order["priority"] == "earliest" else -day,
                             key, left, held))
        elif held:
            return False
    demand = case.order["qty"]
    if claim == "shortage":
        return not market.held and sum(left for _, _, left, _ in eligible) < demand
    if claim != "filled" or sum(market.held.values()) != demand:
        return False
    return not any(a[:2] < b[:2] and a[2] and b[3] for a in eligible for b in eligible)


def plan(order, lots):
    keys = sorted(lots)
    keys.sort(key=lambda k: lots[k][1], reverse=order["priority"] == "latest")
    remaining = order["qty"]
    pick = {}
    for key in keys:
        sku, day, units = lots[key]
        if sku == order["sku"] and day >= order["min_day"] and units and remaining:
            pick[key] = min(remaining, units)
            remaining -= pick[key]
    return {"op": "shortage"} if remaining else {"op": "submit", "pick": pick}


def baseline(order, history):
    if not history or "lots" not in history[-1]["observation"]:
        return {"op": "inspect"}
    return plan(order, history[-1]["observation"]["lots"])


def trial(case, name, policy):
    start = time.monotonic()
    market = Market(case)
    history = []
    status = "step_limit"
    for _ in range(9):
        try:
            action = policy(case.order.copy(), json.loads(json.dumps(history)))
        except (OSError, RuntimeError, TimeoutError) as exc:
            history.append({"observation": {"provider_error": type(exc).__name__}})
            status = "provider_error"
            break
        obs = market.apply(action)
        history.append({"action": action, "observation": obs})
        if "terminal" in obs:
            status = obs["terminal"] if grade(case, market, obs["terminal"]) else "wrong_state"
            break
        if name == "fixed" and "rejected" in obs:
            status = "rejected"
            break
    obs = [event["observation"] for event in history]
    success = status in ("filled", "shortage")
    rejected = sum("rejected" in event for event in obs)
    illegal = sum("illegal" in event for event in obs)
    return dict(seed=case.seed, policy=name, status=status, success=success, steps=len(obs),
                model_decisions=len(obs) if name=="codex" else 0,
                tools=sum(event.get("action", {}).get("op") in ("inspect", "submit")
                          for event in history if isinstance(event.get("action"), dict)),
                illegal=illegal, rejected=rejected, errors=illegal+rejected+int(status=="wrong_state"),
                recovered=int(success and rejected>0), elapsed_s=time.monotonic()-start,
                history=history, stock=market.stock, held=market.held,
                model=None, usage=None, cost=None)
