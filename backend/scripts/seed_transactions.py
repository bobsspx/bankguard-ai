import random
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.account import Account
from app.models.device import Device
from app.models.transaction import Transaction


SEED = 20261001
ACCOUNT_COUNT = 20
TRANSACTION_COUNT = 300


def money(value: float) -> Decimal:
    return Decimal(
        f"{value:.2f}"
    )


def main():
    rng = random.Random(SEED)

    with SessionLocal() as db:
        existing = db.scalar(
            select(Account).where(
                Account.account_ref.like(
                    "BG-ACC-%"
                )
            )
        )

        if existing:
            print(
                "Synthetic BankGuard "
                "dataset already exists."
            )
            return

        accounts = []

        for number in range(
            1,
            ACCOUNT_COUNT + 1,
        ):
            account = Account(
                account_ref=(
                    f"BG-ACC-{number:03d}"
                ),
                customer_ref=(
                    f"BG-CUST-{number:03d}"
                ),
                account_type=(
                    "savings"
                    if number % 2
                    else "current"
                ),
                country_code="LA",
                currency="USD",
                status="active",
            )

            accounts.append(account)

        db.add_all(accounts)
        db.flush()

        devices = []

        for number, account in enumerate(
            accounts,
            start=1,
        ):
            device = Device(
                device_ref=(
                    f"BG-DEV-{number:03d}"
                ),
                account_id=account.id,
                device_type=(
                    "mobile"
                    if number % 3
                    else "desktop"
                ),
                os_name=(
                    "Android"
                    if number % 2
                    else "Windows"
                ),
                trusted=True,
            )

            devices.append(device)

        db.add_all(devices)
        db.flush()

        base_time = datetime.now(
            timezone.utc
        ).replace(
            second=0,
            microsecond=0,
        )

        transactions = []

        normal_types = [
            "transfer",
            "card_payment",
            "cash_withdrawal",
            "bill_payment",
        ]

        normal_channels = [
            "mobile",
            "web",
            "atm",
        ]

        for number in range(
            1,
            TRANSACTION_COUNT + 1,
        ):
            index = (
                number - 1
            ) % ACCOUNT_COUNT

            account = accounts[index]
            device = devices[index]

            suspicious = (
                number % 25 == 0
            )

            if suspicious:
                amount = money(
                    rng.uniform(
                        6500,
                        15000,
                    )
                )

                country_code = rng.choice(
                    [
                        "SG",
                        "CN",
                        "TH",
                    ]
                )

                transaction_type = (
                    "transfer"
                )

                channel = "web"

            else:
                amount = money(
                    rng.uniform(
                        5,
                        1200,
                    )
                )

                country_code = "LA"

                transaction_type = (
                    rng.choice(
                        normal_types
                    )
                )

                channel = rng.choice(
                    normal_channels
                )

            occurred_at = (
                base_time
                - timedelta(
                    minutes=(
                        number * 7
                        + rng.randint(
                            0,
                            20,
                        )
                    )
                )
            )

            transaction = Transaction(
                transaction_ref=(
                    f"BG-TXN-{number:06d}"
                ),
                account_id=account.id,
                device_id=device.id,
                amount=amount,
                currency="USD",
                transaction_type=(
                    transaction_type
                ),
                merchant_category=(
                    "general"
                ),
                country_code=(
                    country_code
                ),
                channel=channel,
                ip_address=(
                    "203.0.113."
                    f"{(number % 200) + 1}"
                ),
                status="completed",
                occurred_at=occurred_at,
            )

            transactions.append(
                transaction
            )

        db.add_all(transactions)
        db.commit()

        print(
            f"Created {ACCOUNT_COUNT} "
            "synthetic accounts."
        )

        print(
            f"Created {ACCOUNT_COUNT} "
            "synthetic devices."
        )

        print(
            f"Created {TRANSACTION_COUNT} "
            "synthetic transactions."
        )


if __name__ == "__main__":
    main()