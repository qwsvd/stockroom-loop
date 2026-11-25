"""One interactive order, isolated SQLite stock, explicit revision-bound consent."""
import json
import secrets
import sqlite3
from datetime import date
from types import SimpleNamespace
from order_language import FIELDS, PRODUCTS, QUESTIONS, evidence, schema
from study import Case, Market, grade, plan


class Session:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE lots(id TEXT PRIMARY KEY, sku TEXT, expiry INTEGER,"
                        " available INTEGER CHECK(available>=0), held INTEGER DEFAULT 0)")
        for i, sku in enumerate(PRODUCTS):
            for j, day in enumerate(("2026-12-15","2026-12-31")):
                self.db.execute("INSERT INTO lots VALUES(?,?,?,?,0)",
                                (f"{i}-{j}",sku,date.fromisoformat(day).toordinal(),8))
        self.db.commit()
        self.pending = None
        self.closed = False
        self.revision = 0
        self.dialogue = []
        self.last_proof = None
        self.asked = None

    def rows(self):
        return self.db.execute("SELECT * FROM lots ORDER BY id").fetchall()

    def interpret(self, text, proposal, active=True):
        if self.closed:
            return {"state":"closed"}
        self.revision += 1
        self.pending = None
        proof = evidence(text)
        if self.dialogue and not text.startswith("重下："):
            # Accept a fragment only for the single previously requested field.
            field = self.asked
            given = [k for k,v in proof["slots"].items() if v is not None]
            if (field and given == [field] and proof["kind"] == "missing"
                    and self.last_proof["kind"] in ("missing","ambiguous","conflict")
                    and sum(v is None for v in self.last_proof["slots"].values())==1):
                slots = dict(self.last_proof["slots"])
                slots[field] = proof["slots"][field]
                proof = {"kind":"clear","target":None,"slots":slots}
            else:
                self.asked = None
                self.last_proof = None
                self.dialogue.append(text)
                return {"state":"blocked","reason":"请用重下：开头重新提供完整订单"}
        self.dialogue.append(text)
        self.last_proof, self.asked = proof, None
        if not schema(proposal):
            return {"state":"blocked","reason":"invalid schema"}
        if proof["kind"]=="unsupported":
            return {"state":"refused","reason":"unsupported language or service"}
        if proposal["kind"]=="unsupported":
            return {"state":"refused","reason":"extractor refused"}
        if proposal != proof:
            return {"state":"blocked","reason":"proposal disagrees with explicit constraints"}
        if proof["kind"]!="clear":
            if active:
                self.asked = proof["target"]
                return {"state":"ask","target":self.asked,"question":QUESTIONS[self.asked]}
            return {"state":"abstain","target":proof["target"]}
        nonce = secrets.token_hex(6)
        slots = proof["slots"].copy()
        self.pending = (nonce, slots)
        return {"state":"preview","revision":self.revision,"slots":slots.copy(),"nonce":nonce}

    def confirm(self, command):
        pending, self.pending = self.pending, None
        if self.closed or not pending or command != "确认 "+pending[0]:
            return {"state":"blocked","reason":"confirmation missing or stale"}
        slots = pending[1]
        order = dict(sku=slots["sku"],qty=slots["qty"],priority=slots["priority"],
                     min_day=date.fromisoformat(slots["date"]).toordinal())
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            initial = {k:[p,d,n] for k,p,d,n,h in self.rows()}
            case = Case(0,order,initial,{})
            market = Market(case)
            action = plan(order,market.apply({"op":"inspect"})["lots"])
            claim = market.apply(action)["terminal"]
            for k,n in market.held.items():
                updated = self.db.execute("UPDATE lots SET available=available-?,held=held+? "
                                          "WHERE id=? AND available>=?",(n,n,k,n))
                if updated.rowcount!=1:
                    raise RuntimeError("stock changed")
            rows = self.rows()
            actual = SimpleNamespace(observed=True, stock={k:[p,d,n] for k,p,d,n,h in rows},
                                     held={k:h for k,p,d,n,h in rows if h})
            if not grade(case,actual,claim):
                raise RuntimeError("database verification failed")
        self.closed = True
        return {"state":claim,"slots":slots,"held":actual.held}
