def take(available, requested):
    """Return (remaining, accepted)."""
    raise NotImplementedError


def loop(policy, apply, budget):
    """Return [(action, observation), ...]."""
    raise NotImplementedError


def verify(initial, remaining, held, order_qty):
    """Two eligible lots in priority order; return True only for the correct fill."""
    raise NotImplementedError
