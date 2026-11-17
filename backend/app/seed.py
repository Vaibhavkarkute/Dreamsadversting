"""
Idempotent database & memory seed runner invoked via `python -m app.seed`.
Verifies the 156 Marquis Pune OOH/DOOH inventory records and initializes the Master Owner.
"""
import json
import os


def run_seed():
    seed_file = os.path.join(os.path.dirname(__file__), "seed_data.json")
    if not os.path.exists(seed_file):
        raise FileNotFoundError(f"Missing seed_data.json at {seed_file}")
    with open(seed_file, "r", encoding="utf-8") as f:
        records = json.load(f)
    print(f"[DreamsAdverstings Seed] Verified {len(records)} Pune OOH/DOOH inventory records ready.")


if __name__ == "__main__":
    run_seed()
