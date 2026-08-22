"""
Turn 267,187 coded 311 rows into documents a retriever can actually grip.

The problem this solves, in plain terms: the 311 export has no sentences in it.
Every row is short category codes — "Rodent Activity", "ISD", "Case Closed. Noted".
2,982 distinct titles exist but the top thirty cover 85% of all rows, and one of
them ("Parking Enforcement") is 60,641 identical strings. Embed the rows and you
get tens of thousands of near-identical vectors, so nearest-neighbour search is a
coin flip and the citations you attach are meaningless even though they're real.

So we don't index rows. We roll rows up into small readable write-ups — one per
street-and-problem, one per problem — that have entities, numbers and time in
them. Each card carries the case IDs it was built from, so a citation points at
records rather than at prose a model wrote.

Two rules from the talk are baked in here rather than bolted on later:
  * filters live at the source, so every card is pre-split by street, problem
    and who reported it — the retriever never has to sort that out;
  * every chunk states its source, its date range and its sensitivity, so the
    answer can show provenance without guessing.

Run:  python cards/build_cards.py
"""

from __future__ import annotations

import csv
import html
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

csv.field_size_limit(10**9)

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data_311_2025.csv"
OUT = ROOT / "cards" / "corpus.jsonl"

# The three channels a member of the public can file through. Everything else is
# a city employee logging their own round. This split matters more than it looks:
# 57% of the file is staff, so without it the app tells someone "eleven neighbours
# reported this too" when seven of them were an inspector. That is the exact false
# comfort the product exists to avoid.
RESIDENT_SOURCES = {"Citizens Connect App", "Constituent Call", "Self Service"}

# Cards are only worth writing where there is a pattern to describe. One lonely
# report is a row, not a story, and padding the corpus with them is how you end
# up back at the noise problem we're trying to escape.
MIN_CASES_PER_STREET = 3
MIN_CASES_PER_CATEGORY = 50

MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]

# Which problems touch someone's home, and therefore shouldn't be described at a
# level that identifies a household. Layer 2 of the guardrail model: sensitivity
# is tagged in the catalogue and enforced at retrieval, not left to the prompt.
SENSITIVE_TITLES = {
    "Poor Conditions of Property",
    "Pest Infestation - Residential",
    "Rodent Activity",
    "Contractor Complaints",
    "Encampments",
    "Needle Pickup",
}


def parse_dt(value: str):
    try:
        return datetime.strptime((value or "")[:19], "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def outcome_of(closure_reason: str) -> str:
    """Boston records the ending in free text that always starts with boilerplate.
    The meaningful word is buried at the end: Resolved, Noted, Invalid, Duplicate."""
    low = (closure_reason or "").lower()
    if "invalid" in low:
        return "invalid"
    if "duplicate" in low:
        return "duplicate"
    if "noted" in low:
        return "noted"
    if "resolved" in low:
        return "resolved"
    return "unclear"


def humanise_hours(hours: float) -> str:
    """639 hours means nothing to a resident. '27 days' does."""
    if hours < 1:
        return f"{round(hours * 60)} minutes"
    if hours < 48:
        return f"{hours:.0f} hours"
    return f"{hours / 24:.0f} days"


def month_span(months: list[int]) -> str:
    """Describe when things cluster, in words rather than a histogram."""
    if not months:
        return ""
    uniq = sorted(set(months))
    if len(uniq) == 1:
        return f"all in {MONTHS[uniq[0] - 1]}"
    # Contiguous run reads as a season; scattered months read as year-round.
    if uniq == list(range(uniq[0], uniq[-1] + 1)) and len(uniq) <= 5:
        return f"clustered {MONTHS[uniq[0] - 1]} to {MONTHS[uniq[-1] - 1]}"
    return "spread across the year"


class Bucket:
    """Everything we accumulate about one street-and-problem, or one problem."""

    __slots__ = ("rows", "resident", "staff", "closed", "outcomes",
                 "hours", "months", "ids", "departments", "overdue", "coords")

    def __init__(self) -> None:
        self.rows = 0
        self.resident = 0
        self.staff = 0
        self.closed = 0
        self.outcomes: defaultdict[str, int] = defaultdict(int)
        self.hours: list[float] = []
        self.months: list[int] = []
        self.ids: list[str] = []
        self.departments: defaultdict[str, int] = defaultdict(int)
        self.overdue = 0
        self.coords: list[tuple[float, float]] = []

    def add(self, row: dict) -> None:
        self.rows += 1
        if row["source"] in RESIDENT_SOURCES:
            self.resident += 1
        else:
            self.staff += 1
        if row["on_time"] == "OVERDUE":
            self.overdue += 1
        if row["department"]:
            self.departments[row["department"]] += 1

        opened = parse_dt(row["open_dt"])
        if opened:
            self.months.append(opened.month)

        if row["case_status"] == "Closed":
            self.closed += 1
            self.outcomes[outcome_of(row["closure_reason"])] += 1
            closed_at = parse_dt(row["closed_dt"])
            if opened and closed_at:
                self.hours.append((closed_at - opened).total_seconds() / 3600)

        # Capped: a citation list is for checking our work, not for shipping the
        # whole table back to the browser.
        if len(self.ids) < 40 and row["case_enquiry_id"]:
            self.ids.append(row["case_enquiry_id"])

        try:
            lat, lon = float(row["latitude"]), float(row["longitude"])
            if lat and lon and len(self.coords) < 200:
                self.coords.append((lat, lon))
        except (ValueError, TypeError):
            pass

    @property
    def top_department(self) -> str:
        return max(self.departments, key=self.departments.get) if self.departments else ""

    @property
    def centroid(self):
        if not self.coords:
            return None
        return (round(sum(c[0] for c in self.coords) / len(self.coords), 6),
                round(sum(c[1] for c in self.coords) / len(self.coords), 6))


def outcome_sentence(bucket: Bucket) -> str:
    """State how things ended, and say plainly when 'closed' didn't mean 'fixed'."""
    if not bucket.closed:
        return "None of them have been closed yet."
    parts = []
    noted = bucket.outcomes.get("noted", 0)
    resolved = bucket.outcomes.get("resolved", 0)
    invalid = bucket.outcomes.get("invalid", 0)
    if resolved:
        parts.append(f"{resolved} closed as resolved")
    if noted:
        # The phrasing matters. "Noted" is Boston's word; what it means to the
        # person who reported it is that nothing happened, and the card says so.
        parts.append(f"{noted} closed as noted only, meaning the report was "
                     f"recorded but no fix was logged")
    if invalid:
        parts.append(f"{invalid} closed as invalid")
    return "Of those closed, " + "; ".join(parts) + "." if parts else ""


def street_card(street: str, title: str, bucket: Bucket) -> dict:
    """One street, one problem, one year — written as a short paragraph."""
    who = []
    if bucket.resident:
        who.append(f"{bucket.resident} {'report was' if bucket.resident == 1 else 'reports were'} "
                   f"filed by residents")
    if bucket.staff:
        who.append(f"{bucket.staff} logged by city staff")
    who_text = " and ".join(who) if who else f"{bucket.rows} reports"

    lines = [
        f"On {street}, {bucket.rows} {title.lower()} "
        f"{'report' if bucket.rows == 1 else 'reports'} were filed in 2025 — {who_text}."
    ]

    span = month_span(bucket.months)
    if span:
        lines.append(f"They were {span}.")

    if bucket.top_department:
        lines.append(f"{bucket.top_department} is the department that handles these.")

    if bucket.hours:
        lines.append(f"The typical case here closed in "
                     f"{humanise_hours(statistics.median(bucket.hours))}.")

    ending = outcome_sentence(bucket)
    if ending:
        lines.append(ending)

    if bucket.overdue:
        lines.append(f"{bucket.overdue} of them missed the city's own deadline.")

    still_open = bucket.rows - bucket.closed
    if still_open:
        lines.append(f"{still_open} {'is' if still_open == 1 else 'are'} still open.")

    return {
        "id": f"street::{street}::{title}",
        "kind": "street_pattern",
        "text": " ".join(lines),
        # Metadata is the filter surface. Everything a query needs to narrow on
        # lives here so the narrowing happens before retrieval, not after it.
        "street": street,
        "case_title": title,
        "department": bucket.top_department,
        "total": bucket.rows,
        "resident_reports": bucket.resident,
        "staff_reports": bucket.staff,
        "still_open": still_open,
        "noted_only": bucket.outcomes.get("noted", 0),
        "centroid": bucket.centroid,
        "case_ids": bucket.ids,
        "sensitivity": "address_level" if title in SENSITIVE_TITLES else "public",
        "source": "Analyze Boston · 311 Service Requests",
        "date_range": "2025-01-01 to 2025-12-31",
    }


def category_card(title: str, bucket: Bucket) -> dict:
    """One problem, citywide — the context that makes a street card mean something."""
    pct_resident = round(bucket.resident / bucket.rows * 100)
    noted = bucket.outcomes.get("noted", 0)
    noted_pct = round(noted / bucket.closed * 100) if bucket.closed else 0

    lines = [
        f'"{title}" is how Boston 311 categorises this kind of report. '
        f"Across the city there were {bucket.rows:,} of them in 2025, "
        f"{pct_resident}% filed by residents rather than city staff."
    ]
    if bucket.top_department:
        lines.append(f"They are handled by {bucket.top_department}.")
    if bucket.hours:
        lines.append(f"Citywide, the typical case closes in "
                     f"{humanise_hours(statistics.median(bucket.hours))}.")
    if bucket.closed and noted_pct:
        lines.append(f"{noted_pct}% of closed cases in this category ended as "
                     f"noted only — recorded, with no fix logged.")
    if bucket.overdue:
        lines.append(f"{round(bucket.overdue / bucket.rows * 100)}% missed the "
                     f"city's target response time.")

    return {
        "id": f"category::{title}",
        "kind": "category",
        "text": " ".join(lines),
        "street": "",
        "case_title": title,
        "department": bucket.top_department,
        "total": bucket.rows,
        "resident_reports": bucket.resident,
        "staff_reports": bucket.staff,
        "still_open": bucket.rows - bucket.closed,
        "noted_only": noted,
        "centroid": None,
        "case_ids": bucket.ids[:10],
        "sensitivity": "public",
        "source": "Analyze Boston · 311 Service Requests",
        "date_range": "2025-01-01 to 2025-12-31",
    }


def main() -> None:
    if not SRC.exists():
        sys.exit(f"Missing {SRC}. Copy the 2025 311 CSV there first.")

    streets: defaultdict[tuple[str, str], Bucket] = defaultdict(Bucket)
    categories: defaultdict[str, Bucket] = defaultdict(Bucket)

    read = 0
    with SRC.open(newline="", encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            read += 1
            title = (row.get("case_title") or "").strip()
            if not title:
                continue
            categories[title].add(row)
            street = html.unescape((row.get("location_street_name") or "").strip())
            if street:
                streets[(street, title)].add(row)

    cards = []
    for (street, title), bucket in streets.items():
        if bucket.rows >= MIN_CASES_PER_STREET:
            cards.append(street_card(street, title, bucket))
    for title, bucket in categories.items():
        if bucket.rows >= MIN_CASES_PER_CATEGORY:
            cards.append(category_card(title, bucket))

    with OUT.open("w", encoding="utf-8") as fh:
        for card in cards:
            fh.write(json.dumps(card) + "\n")

    street_cards = sum(1 for c in cards if c["kind"] == "street_pattern")
    category_cards = len(cards) - street_cards
    print(f"read      {read:,} rows")
    print(f"wrote     {len(cards):,} cards  ->  {OUT}")
    print(f"          {street_cards:,} street patterns · {category_cards} categories")
    print(f"sensitive {sum(1 for c in cards if c['sensitivity'] == 'address_level'):,} "
          f"cards tagged address-level")
    print()
    print("--- sample street card ---")
    sample = max((c for c in cards if c["kind"] == "street_pattern"),
                 key=lambda c: c["resident_reports"])
    print(sample["text"])


if __name__ == "__main__":
    main()
