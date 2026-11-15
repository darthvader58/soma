"""Finite-volume lunar data-delivery planning under declared assumptions."""

__version__ = "0.1.0"


def plan_delivery(scenario, **kwargs):
    """Validate a standalone scenario and return the current engine result."""
    from soma.engine import plan_delivery as plan

    return plan(scenario, **kwargs)
