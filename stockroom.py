"""Synthetic order and capability-limited SQLite environment."""
import sqlite3

ORDER = 5
DATE = "2026-06-01"
SEED = (
    ("B7", "tea", "2026-06-09", 6),
    ("H4", "tea", "2026-06-03", 4),
    ("X3", "tea", "2026-05-31", 9),
    ("M8", "soap", "2026-06-01", 8),
)
GOAL = """Reserve exactly 5 tea units valid on 2026-06-01. Use earliest expiry first;
break ties by lot ID. Stock can change before reservation. Choose one JSON object:
{"op":"inspect"}, {"op":"reserve","lot":"ID","qty":1}, or {"op":"finish"}.
inspect returns [lot, product, expiry, available, reserved] rows. Use feedback.
Only finish once the order is correct. Reply with the JSON object alone."""


class Stockroom:
    def __init__(self, race=True):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE lots(id TEXT PRIMARY KEY, product TEXT, expiry TEXT,"
                        "available INTEGER CHECK(available>=0), held INTEGER DEFAULT 0)")
        self.db.executemany("INSERT INTO lots VALUES(?,?,?,?,0)", SEED)
        self.db.commit()
        self.pending_sale = race
        self.sold = 0

    def snapshot(self):
        return self.db.execute("SELECT * FROM lots ORDER BY id").fetchall()

    def act(self, action):
        if action == {"op": "inspect"}:
            return {"lots": self.snapshot()}
        if not isinstance(action, dict) or set(action) != {"op", "lot", "qty"}:
            return {"error": "unknown action or fields"}
        lot, qty = action["lot"], action["qty"]
        if (action["op"] != "reserve" or type(qty) is not int or
                not 1 <= qty <= ORDER or not isinstance(lot, str) or
                not lot.isascii() or not 1 <= len(lot) <= 16):
            return {"error": "invalid reservation"}
        if self.pending_sale:
            with self.db:
                self.db.execute("UPDATE lots SET available=available-3 WHERE id='H4'")
            self.sold = 3
            self.pending_sale = False
        with self.db:
            changed = self.db.execute(
                "UPDATE lots SET available=available-?, held=held+? "
                "WHERE id=? AND product='tea' AND expiry>=? AND available>=? "
                "AND (SELECT SUM(held) FROM lots)+?<=?",
                (qty, qty, lot, DATE, qty, qty, ORDER)).rowcount
        if changed:
            return {"reserved": qty, "lot": lot}
        return {"error": "quantity, eligibility or order limit failed; inspect current stock"}


def verified(room):
    """Reference plan from initial supply and the external sale, independent of dispatch."""
    remaining = ORDER
    expected = {}
    for lot, product, expiry, units in sorted(SEED, key=lambda row: (row[2], row[0])):
        supply = units - (room.sold if lot == "H4" else 0)
        pick = min(supply, remaining) if product == "tea" and expiry >= DATE else 0
        expected[lot] = (product, expiry, supply - pick, pick)
        remaining -= pick
    actual = {lot: tuple(values) for lot, *values in room.snapshot()}
    return remaining == 0 and expected == actual

