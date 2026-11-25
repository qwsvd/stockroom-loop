"""Paired Chinese NLU benchmark. Default replays the archived model replies offline."""
import argparse
from collections import Counter
from contextlib import closing
from datetime import date
import json
import os
from pathlib import Path
import random
import subprocess
import time

from live_study import Client, native_cli
from order_language import FIELDS, PROMPT, evidence, schema
from order_session import Session

ROOT = Path(__file__).resolve().parent / "evidence" / "v03"


def read(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def write(stream, value):
    print(json.dumps(value, ensure_ascii=False, separators=(",",":")),file=stream,flush=True)


def message(dialogues):
    return PROMPT + "\n" + json.dumps(dialogues,ensure_ascii=False)


def proposals(raw, count):
    if not isinstance(raw,list) or len(raw)!=count:
        return [None]*count
    return raw


def decode_batch(reply, count):
    def unique(pairs):
        obj = dict(pairs)
        if len(obj) != len(pairs):
            raise ValueError("duplicate JSON key")
        return obj
    try:
        raw = json.loads(reply, object_pairs_hook=unique) if len(reply)<=16000 else None
    except (ValueError, RecursionError):
        raw = None
    return proposals(raw,count)


def matches_authorized_fill(initial, final, slots):
    """Evaluation-only reference: expand eligible units and compare every committed row."""
    if slots is None:
        return False
    minimum = date.fromisoformat(slots["date"]).toordinal()
    units = []
    for lot, sku, expiry, available, held in initial:
        if sku == slots["sku"] and expiry >= minimum:
            rank = expiry if slots["priority"] == "earliest" else -expiry
            units.extend([(rank, lot)] * available)
    if len(units) < slots["qty"]:
        return False
    picks = Counter(lot for _,lot in sorted(units)[:slots["qty"]])
    expected = [(lot,sku,expiry,available-picks[lot],held+picks[lot])
                for lot,sku,expiry,available,held in initial]
    return final == expected


def paired(case, method, first, follow=None):
    session = Session()
    with closing(session.db):
        initial = session.rows()
        first_view = session.interpret(case["text"],first,method=="C")
        events = [dict(first_view)]
        view = first_view
        answered = (view["state"]=="ask" and view["target"]==case["target"] and case["answer"] is not None)
        if answered:
            events.append({"answer":case["answer"]})
            view = session.interpret(case["answer"],follow,False)
            events.append(dict(view))
        preview = view["state"]=="preview"
        authorized = (case["kind"]=="clear" or answered) and case["authorized"] is not None
        right = authorized and preview and view["slots"]==case["authorized"]
        if preview:
            events[-1].pop("nonce")
            events.append({"confirmed":right})
            if right:
                view = session.confirm("确认 "+view["nonce"])
                events.append(view)
        final = session.rows()
    wrote = initial != final
    outcome = view["state"]
    verified = wrote and right and outcome=="filled" and matches_authorized_fill(initial,final,case["authorized"])
    return dict(id=case["id"],split=case["split"],method=method,kind=case["kind"],
                proposal=first,events=events,final_rows=final,write=wrote,
                unsafe=wrote and not verified,
                filled=verified,wrong_preview=preview and not right,
                asked=first_view["state"]=="ask",targeted=answered,
                correct_refusal=outcome=="refused" and case["kind"]=="unsupported",
                terminal="unconfirmed" if preview and not right else outcome)


def batches(cases):
    for split in ("dev","holdout"):
        items = [c for c in cases if c["split"]==split]
        random.Random(137).shuffle(items)
        for i in range(0,len(items),10):
            yield items[i:i+10]


def dialogue(c, question=None):
    if question:
        return [c["text"],question,c["answer"]]
    return [c["text"]]


def run_campaign(cases, infer):
    results = []
    for batch in batches(cases):
        initial = infer(batch,[dialogue(c) for c in batch],"initial")
        waiting = []
        for c,p in zip(batch,initial,strict=True):
            b = paired(c,"B",p)
            results.append(b)
            session = Session()
            with closing(session.db):
                view = session.interpret(c["text"],p)
            if view["state"]=="ask" and view["target"]==c["target"] and c["answer"]:
                waiting.append((c,view["question"]))
        second = {}
        if waiting:
            group = [c for c,q in waiting]
            replies = infer(group,[dialogue(c,q) for c,q in waiting],"followup")
            second = {c["id"]:v for c,v in zip(group,replies,strict=True)}
        results.extend(paired(c,"C",p,second.get(c["id"])) for c,p in zip(batch,initial,strict=True))
    return results


def connect():
    cli = native_cli()
    if not cli:
        raise RuntimeError("native Codex CLI missing")
    env = {k:v for k,v in os.environ.items() if k.upper() not in ("OPENAI_API_KEY","CODEX_API_KEY")}
    login = subprocess.run([cli,"login","status"],env=env,capture_output=True,timeout=15)
    if login.returncode or b"Logged in using ChatGPT" not in login.stdout+login.stderr:
        raise RuntimeError("ChatGPT login required")
    version = subprocess.check_output([cli,"--version"],env=env,text=True).strip()
    return Client(cli,env),version


def collect(path,cases):
    client,version = connect()
    with path.open("x",encoding="utf-8") as stream:
        def infer(group, dialogs, phase):
            start = time.monotonic()
            error = None
            try:
                client.request(message(dialogs),16000)
            except (OSError, RuntimeError, TimeoutError) as exc:
                error = type(exc).__name__
                raise
            finally:
                row = dict(ids=[c["id"] for c in group],phase=phase, cli=version,dialogs=dialogs,
                           wall_s=time.monotonic()-start,error=error,**client.calls[-1])
                write(stream,row)
                print(row["ids"][0],phase,row["wall_s"],error,flush=True)
            return decode_batch(row["reply"],len(group))
        run_campaign(cases,infer)


def replay(cases, calls):
    entries = iter(calls)
    def infer(group,dialogs,phase):
        r=next(entries)
        if r["ids"]!=[c["id"] for c in group] or r["dialogs"]!=dialogs or r["phase"]!=phase or r["error"]:
            raise ValueError("campaign evidence mismatch")
        return decode_batch(r["reply"],len(group))
    rows = [paired(c,"A",evidence(c["text"])) for c in cases] + run_campaign(cases,infer)
    if next(entries,None) is not None:
        raise ValueError("unexpected extra call")
    return rows


def metrics(rows,cases):
    counts=Counter()
    for r in rows:
        c=cases[r["id"]]
        p=r["proposal"]
        slots=p["slots"] if schema(p) else {}
        pred=p["kind"] if schema(p) else None
        counts.update(n=1,clear=c["kind"]=="clear",needs=c["target"] is not None,
                      unsupported=c["kind"]=="unsupported",writes=r["write"],unsafe=r["unsafe"],
                      right_questions=r["targeted"],questions=r["asked"],unnecessary=r["asked"] and c["kind"]=="clear",
                      previews=any(e.get("state")=="preview" for e in r["events"]),wrong_previews=r["wrong_preview"],
                      slots=sum(k in slots and slots[k]==v for k,v in c["initial"].items()),
                      conflict_correct=(pred=="conflict")== (c["kind"]=="conflict"),
                      unsupported_tp=pred=="unsupported" and c["kind"]=="unsupported",
                      correct_refusals=r["correct_refusal"],fills=r["filled"])
    return dict(counts)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collect",type=Path)
    parser.add_argument("--save-results",type=Path)
    args=parser.parse_args()
    cases=read(ROOT/"orders.jsonl")
    if args.collect:
        collect(args.collect,cases)
    else:
        rows=replay(cases,read(ROOT/"calls.jsonl"))
        if args.save_results:
            with args.save_results.open("x",encoding="utf-8") as stream:
                for row in rows:
                    write(stream,row)
        elif json.loads(json.dumps(rows))!=read(ROOT/"results.jsonl"):
            raise ValueError("replayed results differ")
        lookup={c["id"]:c for c in cases}
        for split in ("dev","holdout"):
            for method in "ABC":
                print(split,method,metrics([r for r in rows if (r["split"],r["method"])==(split,method)],lookup))
