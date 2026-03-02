
"""

Broker factory — single entry point for broker instantiation.
Backtest engine and strategy layer use only this module.
Never import broker classes directly outside this file.

Usage:
    from factory import get_broker
    broker = get_broker("upstox")
    result = broker.calculate_trade_cost(100, 110, 50, "delivery")

Supported brokers:
    "upstox"    → UpstoxBroker
    "groww"     → GrowwBroker
    "angel_one" → AngelOneBroker

To add a new broker:
    1. Create broker file (e.g. zerodha.py)
    2. Import class here
    3. Add entry to BROKER_REGISTRY
    That's it. Nothing else changes.
"""

from .upstox import UpstoxBroker
from .groww import GrowwBroker
from .angel import AngelOneBroker
from .base_broker import BaseBroker


# ─────────────────────────────────────────────
# BROKER REGISTRY
# Add new brokers here only. Nothing else needs to change.
# ─────────────────────────────────────────────

BROKER_REGISTRY = {
    "upstox":    UpstoxBroker,
    "groww":     GrowwBroker,
    "angel_one": AngelOneBroker,
}


def get_broker(broker_name: str) -> BaseBroker:
    """
    Return an instance of the requested broker.

    Args:
        broker_name: One of "upstox", "groww", "angel_one"

    Returns:
        Broker instance ready for calculation.

    Raises:
        ValueError: If broker_name is not registered.

    Example:
        broker = get_broker("upstox")
        result = broker.calculate_trade_cost(100, 110, 50, "delivery")
    """
    key = broker_name.strip().lower()

    if key not in BROKER_REGISTRY:
        supported = list(BROKER_REGISTRY.keys())
        raise ValueError(
            f"Unknown broker '{broker_name}'. "
            f"Supported brokers: {supported}"
        )

    return BROKER_REGISTRY[key]()


def list_brokers() -> list:
    """Return list of all registered broker names."""
    return list(BROKER_REGISTRY.keys())