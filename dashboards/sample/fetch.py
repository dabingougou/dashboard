"""Fetch step for the sample dashboard.

Returns fake, clearly labeled SAMPLE DATA. No network or accounts needed.
A real dashboard would call an API here and return plain JSON serializable
data (dicts, lists, strings, numbers, booleans, None). Return times as ISO
strings and format them in layout.py with ctx.format_time().
"""

import random


def fetch(ctx):
    if ctx.settings.get("simulate_failure"):
        raise RuntimeError("simulated fetch failure (simulate_failure: true)")

    # Seed on the hour so the numbers change slowly but deterministically.
    rng = random.Random(ctx.now.strftime("%Y%m%d%H"))
    return {
        "label": "SAMPLE DATA",
        "generated_at": ctx.now.isoformat(),
        "headline": "Everything on this screen is made up.",
        "metrics": [
            {"name": "Widgets made", "value": rng.randint(100, 999)},
            {"name": "Queue length", "value": rng.randint(0, 40)},
            {"name": "Success rate", "value": f"{rng.uniform(90, 100):.1f}%"},
        ],
        "notes": [
            "This is a sample note with enough words to show line wrapping on the e ink screen.",
            "Second sample note.",
            "Third sample note.",
        ],
        "table": {
            "columns": ["Item", "Status", "Count"],
            "rows": [[f"Sample item {i}", rng.choice(["ok", "pending", "late"]), rng.randint(1, 99)]
                     for i in range(1, 4)],
        },
    }
