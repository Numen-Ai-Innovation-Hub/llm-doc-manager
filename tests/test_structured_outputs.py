"""Test file for Structured Outputs implementation."""


def calculate_discount(price: float, discount_percent: int) -> float:
    """Calculate final price after applying percentage discount.

    Args:
        price (float): Original price before discount
        discount_percent (int): Discount percentage (0-100)

    Returns:
        float: Final price after discount applied

    Raises:
        ValueError: If discount_percent is not between 0 and 100
    """
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Discount must be between 0 and 100")
    return price * (1 - discount_percent / 100)


class ShoppingCart:
    """Manages items in a shopping cart."""

    def __init__(self):
        self.items = []
        self.total = 0.0

    def add_item(self, item: str, price: float):
        self.items.append({"item": item, "price": price})
        self.total += price