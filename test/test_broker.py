"""
Interactive broker test file.

Run this file.
Enter values manually.
Compare output with official calculator.
"""

from app.adapters.brokers.upstox import UpstoxBroker
from app.adapters.brokers.groww import GrowwBroker
from app.adapters.brokers.angel import AngelOneBroker  


def main():
    #broker = UpstoxBroker()
    #broker = GrowwBroker()  # Uncomment to test Groww instead
    broker = AngelOneBroker()  # Uncomment to test Angel One instead
    

    print("\n=== Angel One Brokerage Test ===")

    trade_type = input("Trade Type (delivery/intraday): ").strip().lower()
    buy_price = float(input("Buy Price: "))
    sell_price = float(input("Sell Price: "))
    quantity = int(input("Quantity: "))

    result = broker.calculate_trade_cost(
        buy_price=buy_price,
        sell_price=sell_price,
        quantity=quantity,
        trade_type=trade_type,
    )

    print("\n--- Result Breakdown ---")
    for key, value in result.items():
        print(f"{key:15}: {value}")

    print("\nCompare this with official Upstox calculator.")


if __name__ == "__main__":
    main()