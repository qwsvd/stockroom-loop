import json
import unittest
from agent import run
from stockroom import Stockroom, verified


def reserve(lot, qty):
    return {"op": "reserve", "lot": lot, "qty": qty}


class LoopTests(unittest.TestCase):
    def room(self, race=True):
        room = Stockroom(race)
        self.addCleanup(room.db.close)
        return room

    def scripted(self, room, actions):
        replies = iter(map(json.dumps, actions))
        return run(room, lambda *_: next(replies), len(actions))

    def test_fixed_plan_pair(self):
        actions = [reserve("H4", 4), reserve("B7", 1), {"op": "finish"}]
        for race, status in [(False, "verified"), (True, "wrong_state")]:
            with self.subTest(race=race):
                result = self.scripted(self.room(race), actions)
                self.assertEqual(result["status"], status)

    def test_feedback_delivery(self):
        room = self.room()
        proposed = iter([{"op":"inspect"}, reserve("H4", 4), {"op":"inspect"},
                         reserve("H4", 1), reserve("B7", 4), {"op":"finish"}])
        def policy(goal, history):
            seen = json.loads(history)
            if len(seen) == 2:
                self.assertIn("error", seen[-1]["observation"])
            if len(seen) == 3:
                self.assertIn(["H4","tea","2026-06-03",1,0], seen[-1]["observation"]["lots"])
            return json.dumps(next(proposed))
        self.assertEqual(run(room, policy)["status"], "verified")

    def test_reject_actions_without_partial_reservation(self):
        room = self.room(False)
        before = room.snapshot()
        for action in [None, [], {}, {"op":"inspect","sql":"ignored"},
                       reserve("B7", True), reserve("B7", 0), reserve("B7", -1),
                       reserve("B7", 1.0), reserve("B7", 6), reserve("H4", 5),
                       reserve("M8", 1), reserve("X3", 1), reserve("missing", 1),
                       reserve("\ud800", 1)]:
            self.assertIn("error", room.act(action))
            self.assertEqual(before, room.snapshot())

    def test_model_claim_and_quantity_alone_are_insufficient(self):
        room = self.room(False)
        room.act(reserve("B7", 5))
        self.assertFalse(verified(room))
        self.assertIn("error", room.act(reserve("H4", 1)))
        self.assertEqual(self.scripted(room, [{"op":"finish"}])["status"], "wrong_state")

    def test_corruption_detected(self):
        room = self.room(False)
        room.act(reserve("H4", 4))
        room.act(reserve("B7", 1))
        self.assertTrue(verified(room))
        room.db.execute("UPDATE lots SET available=0 WHERE product='soap'")
        self.assertFalse(verified(room))

    def test_invalid_output_consumes_budget(self):
        for raw in ["broken", "x"*1025, "["*1000]:
            result = run(self.room(), lambda *_: raw, 2)
            self.assertEqual(result["status"], "step_limit")
            self.assertEqual(len(result["history"]), 2)

    def test_provider_failure(self):
        def unavailable(*_):
            raise TimeoutError("private diagnostic")
        result = run(self.room(), unavailable)
        self.assertEqual(result["status"], "provider_error")
        self.assertNotIn("private diagnostic", str(result))

    def test_limit_range(self):
        for limit in [False, 0, 13]:
            with self.assertRaises(ValueError):
                run(self.room(), None, limit)


if __name__ == "__main__":
    unittest.main()
