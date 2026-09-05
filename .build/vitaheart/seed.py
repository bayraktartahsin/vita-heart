"""Seed the demo household. Idempotent.

    python -m vitaheart.seed
"""
from __future__ import annotations

from . import config, store

DEMO_PROFILE = {
    "code": config.DEMO_HOUSEHOLD,
    "name": "Ahmet",
    "age": 72,
    "lang": "tr",
    "tz_offset_hours": 3,
    "resting_hr": 61,
    "family": [{"name": "Selin", "relation": "daughter", "city": "Ankara"}],
}


def main() -> None:
    store.put_profile(config.DEMO_HOUSEHOLD, DEMO_PROFILE)
    if not store.latest_message(config.DEMO_HOUSEHOLD):
        store.post_message(config.DEMO_HOUSEHOLD, "Selin", "Baba, akşam arayacağım. İlaçlarını unutma.")
    print(f"seeded household {config.DEMO_HOUSEHOLD} in table {config.TABLE} ({config.REGION})")


if __name__ == "__main__":
    main()
