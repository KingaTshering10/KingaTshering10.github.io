"""Financial calculations for collection receipts and payment obligations.

All arithmetic is Decimal quantised to 2 dp (ROUND_HALF_UP). Every deduction
is a separate, visible line — nothing is netted invisibly.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import CollectionRecord

TWO_DP = Decimal("0.01")


def q2(value: Decimal) -> Decimal:
    return value.quantize(TWO_DP, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ReceiptAmounts:
    gross_amount: Decimal
    transport_deduction: Decimal
    platform_fee: Decimal
    other_deduction: Decimal
    net_amount_due: Decimal


def compute_receipt(
    accepted_quantity: Decimal,
    unit_price: Decimal,
    transport_deduction: Decimal = Decimal("0"),
    other_deduction: Decimal = Decimal("0"),
    platform_fee_percent: Decimal | None = None,
) -> ReceiptAmounts:
    if platform_fee_percent is None:
        platform_fee_percent = Decimal(get_settings().platform_fee_percent)
    gross = q2(accepted_quantity * unit_price)
    fee = q2(gross * platform_fee_percent / Decimal("100"))
    transport = q2(transport_deduction)
    other = q2(other_deduction)
    net = q2(gross - transport - fee - other)
    if net < 0:
        raise ValueError("Deductions exceed the gross amount; check the entered values.")
    return ReceiptAmounts(gross, transport, fee, other, net)


def next_receipt_number(db: Session, year: int) -> str:
    prefix = f"DAL-{year}-"
    count = (
        db.scalar(
            select(func.count())
            .select_from(CollectionRecord)
            .where(CollectionRecord.receipt_number.like(f"{prefix}%"))
        )
        or 0
    )
    return f"{prefix}{count + 1:06d}"
