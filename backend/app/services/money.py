"""Money helpers. Integer paise everywhere; Decimal only inside calculations (D-005)."""

from decimal import ROUND_HALF_UP, Decimal

BP_DENOMINATOR = Decimal(10000)


def round_paise(value: Decimal) -> int:
    """Round to a whole paisa, half away from zero (0.5 → 1)."""
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def apply_bp(amount_paise: int, rate_bp: int | Decimal) -> int:
    """`amount × rate`, where rate is in basis points (500 = 5%), rounded to a paisa."""
    return round_paise(Decimal(amount_paise) * Decimal(rate_bp) / BP_DENOMINATOR)


def paise_to_display(paise: int) -> str:
    """Format with Indian digit grouping: 123900050 → '₹12,39,000.50'."""
    sign = "-" if paise < 0 else ""
    rupees, rem = divmod(abs(paise), 100)
    digits = str(rupees)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join([*groups, tail])
    return f"{sign}₹{digits}.{rem:02d}"
