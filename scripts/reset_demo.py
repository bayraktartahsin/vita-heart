#!/usr/bin/env python3
"""Reset the demo household to a clean, seeded state. Idempotent.

    python scripts/reset_demo.py            # wipe AHMET1's meds, doses, events, messages, check-ins; reseed
    python scripts/reset_demo.py --keep-meds

Run before every recording. Never touches any other household.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))

from boto3.dynamodb.conditions import Key  # noqa: E402

from vitaheart import config, seed, store  # noqa: E402

KEEP_MEDS = "--keep-meds" in sys.argv
PREFIXES = ("DOSE#", "EV#", "MSG#", "CHECKIN#") + (() if KEEP_MEDS else ("MED#",))


def main() -> None:
    code = config.DEMO_HOUSEHOLD
    t = store.table()
    pk = f"HH#{code}"
    deleted = 0
    for prefix in PREFIXES:
        r = t.query(KeyConditionExpression=Key("PK").eq(pk) & Key("SK").begins_with(prefix))
        for item in r.get("Items", []):
            t.delete_item(Key={"PK": pk, "SK": item["SK"]})
            deleted += 1
    seed.main()
    print(f"reset {code}: removed {deleted} item(s), reseeded profile and first message")


if __name__ == "__main__":
    main()
