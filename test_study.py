from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import itertools
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from threading import Barrier
import unittest

from stockroom import Stockroom
from study import Case, Market, baseline, generate, grade, plan, trial


class StudyTests(unittest.TestCase):
    def test_golden_cases_and_reference_enumeration(self):
        lots = {"B": ["tea", 2, 2], "A": ["tea", 2, 1], "C": ["tea", 4, 2],
                "D": ["tea", 0, 4], "E": ["soap", 8, 3]}
        for priority, ranking, golden in [
                ("earliest", "ABC", {"A":1, "B":2}), ("latest", "CAB", {"C":2, "A":1})]:
            for qty in range(1, 7):
                case = Case(0, dict(sku="tea", min_day=1, qty=qty, priority=priority), lots, {})
                market = Market(case)
                market.apply({"op":"inspect"})
                vectors = [v for v in itertools.product(*(range(lots[k][2]+1) for k in ranking))
                           if sum(v) == qty]
                best = max(vectors, default=None)
                if qty == 3:
                    self.assertEqual(dict((k,n) for k,n in zip(ranking,best) if n), golden)
                self.assertEqual(grade(case, market, "shortage"), best is None)
                for v in vectors:
                    candidate = Market(case)
                    candidate.apply({"op":"inspect"})
                    pick = {k:n for k,n in zip(ranking,v) if n}
                    self.assertEqual(candidate.apply({"op":"submit","pick":pick}), {"terminal":"filled"})
                    self.assertEqual(grade(case, candidate, "filled"), v == best)

    def test_mutations_and_atomic_rejection(self):
        case = Case(1, dict(sku="tea", min_day=2, qty=2, priority="earliest"),
                    {"X":["tea",2,1], "Y":["tea",2,3], "Z":["soap",1,0]}, {})
        market = Market(case)
        snapshot = market.apply({"op":"inspect"})["lots"]
        for pick in [{"X":1,"Y":2}, {"X":2}, {"Y":True}, {"Q":1}]:
            market.apply({"op":"submit","pick":pick})
            self.assertEqual(market.stock, snapshot)
            self.assertEqual(market.held, {})
        market.apply(plan(case.order, snapshot))
        self.assertTrue(grade(case, market, "filled"))
        market.stock["Z"][2] += 1
        self.assertFalse(grade(case, market, "filled"))

    def test_illegal_and_stop(self):
        row = trial(generate(0), "codex", lambda *_: None)
        self.assertEqual((row["illegal"], row["steps"], row["status"]), (9,9,"step_limit"))
        row = trial(generate(0), "adaptive", baseline)
        self.assertTrue(row["success"])

    def test_policy_usage_warnings(self):
        from live_study import LIMIT
        for line in ("quota exceeded", "HTTP 429", "status code: 402", "5% remaining",
                     "purchase credits", "rate_limit_exceeded"):
            self.assertRegex(line, LIMIT)
        self.assertNotRegex('{"input_tokens": 12429}', LIMIT)

    def test_random_reference_by_individual_units(self):
        for seed in range(100):
            case = generate(seed)
            row = trial(case, "adaptive", baseline)
            units = []
            for lot, (product, day, supply) in case.lots.items():
                if product == case.order["sku"] and day >= case.order["min_day"]:
                    rank = day if case.order["priority"] == "earliest" else -day
                    units.extend([(rank, lot)] * (supply - case.sale.get(lot, 0)))
            if len(units) < case.order["qty"]:
                self.assertEqual((row["status"], row["held"]), ("shortage", {}))
            else:
                from collections import Counter
                picks = Counter(k for _, k in sorted(units)[:case.order["qty"]])
                self.assertEqual((row["status"], row["held"]), ("filled", picks))

    def test_legacy_sql_competing_connections(self):
        # Same released UPDATE, executed by independent connections on a shared file.
        for second_lot in ("H4", "B7"):
            with self.subTest(second_lot=second_lot), TemporaryDirectory() as tmp:
                path = Path(tmp) / "stock.db"
                initial = Stockroom(False)
                with closing(initial.db), closing(sqlite3.connect(path)) as disk:
                    initial.db.backup(disk)
                barrier = Barrier(2, timeout=10)
                def reserve(lot):
                    room = Stockroom(False)
                    room.db.close()
                    with closing(sqlite3.connect(path, timeout=5)) as room.db:
                        before = room.snapshot()
                        barrier.wait()
                        reply = room.act({"op":"reserve","lot":lot,"qty":4})
                        return before, reply
                with ThreadPoolExecutor(2) as pool:
                    results = list(pool.map(reserve, ["H4", second_lot]))
                self.assertEqual(results[0][0], results[1][0])
                self.assertEqual(sum("reserved" in reply for _,reply in results), 1)
                with closing(sqlite3.connect(path)) as reader:
                    self.assertEqual(reader.execute("SELECT SUM(held), SUM(available) FROM lots").fetchone(), (4,23))

    def test_legacy_sql_lock_contention(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "stock.db"
            room = Stockroom(False)
            with closing(sqlite3.connect(path)) as writer:
                room.db.backup(writer)
                room.db.close()
                with closing(sqlite3.connect(path, timeout=0)) as room.db:
                    writer.execute("BEGIN IMMEDIATE")
                    writer.execute("UPDATE lots SET available=1 WHERE id='H4'")
                    self.assertIn(("H4","tea","2026-06-03",4,0),room.snapshot())
                    action = {"op":"reserve","lot":"H4","qty":4}
                    with self.assertRaises(sqlite3.OperationalError) as caught:
                        room.act(action)
                    self.assertEqual(caught.exception.sqlite_errorcode, sqlite3.SQLITE_BUSY)
                    writer.commit()
                    self.assertIn("error",room.act(action))
                    self.assertIn(("H4","tea","2026-06-03",1,0),room.snapshot())
