"""What changed since the previous output, and the page a reviewer reads.

Three classes of change: listed one by one (added, removed, retracted,
tracking changed), counted per field (OpenAlex drift), and curation
(the maintainer's own). Which change goes where, and why, is stage 12 of
docs/requirements-v1.md section 7.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

Record = dict[str, Any]

# Per listed section. A listed entry costs about 320 characters against
# GitHub's 65,536-character PR body (measured by the first consumer on a
# 410-work widening), so 150 renders near 48 KB and leaves room for long
# titles. Anything beyond is counted, never silently dropped.
LISTED_CAP = 150
MAX_COAUTHORS = 6
# Share of the previous build above which removals draw a warning: a merge
# wave removes a handful, a lost author batch removes dozens.
SHRINK_FRACTION = 0.1


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" + ("" if count == 1 else "s")


def _by_id(records: list[Record]) -> dict[str, Record]:
    return {str(r["id"]): r for r in records if r.get("id")}


def _tracked(record: Record) -> list[str]:
    """Canonical names of the tracked people on a work."""
    authors = record.get("authors") or []
    return sorted({a["tracked_as"] for a in authors if a.get("tracked") and a.get("tracked_as")})


def _authorship(record: Record) -> list[tuple[Any, Any]]:
    return [(a.get("name"), a.get("orcid")) for a in record.get("authors") or []]


@dataclass
class Delta:
    total: int
    previous_total: int | None = None  # None: nothing to compare against
    added: list[Record] = field(default_factory=list)
    removed: list[Record] = field(default_factory=list)
    retracted: list[Record] = field(default_factory=list)  # the flag turned on
    # Works whose set of tracked people differs: (work, tracked before).
    retracked: list[tuple[Record, list[str]]] = field(default_factory=list)
    field_counts: Counter[str] = field(default_factory=Counter)  # drift, by field
    tag_changes: int = 0

    @property
    def first_build(self) -> bool:
        return self.previous_total is None

    @property
    def field_updates(self) -> int:
        return sum(self.field_counts.values())

    @property
    def unchanged(self) -> bool:
        return not (
            self.added
            or self.removed
            or self.retracted
            or self.retracked
            or self.field_counts
            or self.tag_changes
        )

    def warnings(self) -> list[str]:
        if self.previous_total and len(self.removed) > SHRINK_FRACTION * self.previous_total:
            return [
                f"{len(self.removed)} of {self.previous_total} works removed since the "
                "previous output; a degraded fetch reads as mass removals, so check "
                "before merging"
            ]
        return []

    def headline(self) -> str:
        if self.first_build:
            return f"first build, {_plural(self.total, 'work')}, nothing to compare against"
        if self.unchanged:
            return f"no changes, {_plural(self.total, 'work')}"
        parts = [f"{len(self.added)} added", f"{len(self.removed)} removed"]
        if self.retracted:
            parts.append(f"{len(self.retracted)} retracted")
        if self.retracked:
            parts.append(f"{len(self.retracked)} with tracking changed")
        if self.field_counts:
            parts.append(_plural(self.field_updates, "field update"))
        if self.tag_changes:
            parts.append(_plural(self.tag_changes, "tag change"))
        return ", ".join(parts) + f" ({self.previous_total} → {_plural(self.total, 'work')})"


def compute_delta(previous: list[Record] | None, current: list[Record]) -> Delta:
    """Compare two output documents' records by work id.

    Both lists keep their own order (the output is sorted deterministically),
    so listed sections come out in output order and the field table is
    sorted at render time; the same two files always render the same page.
    """
    delta = Delta(total=len(current))
    if previous is None:
        return delta
    old, new = _by_id(previous), _by_id(current)
    delta.previous_total = len(old)
    delta.added = [new[i] for i in new if i not in old]
    delta.removed = [old[i] for i in old if i not in new]
    for work_id, record in new.items():
        before = old.get(work_id)
        if before is None:
            continue
        tracked_before = _tracked(before)
        if tracked_before != _tracked(record):
            delta.retracked.append((record, tracked_before))
        if record.get("is_retracted") and not before.get("is_retracted"):
            delta.retracted.append(record)
        if record.get("tags") != before.get("tags"):
            delta.tag_changes += 1
        for name in sorted(record.keys() | before.keys()):
            if name in ("id", "tags"):
                continue
            if name == "authors":
                # Tracking changes are listed above; here only the names
                # and iDs of the byline count, as drift.
                changed = _authorship(record) != _authorship(before)
            elif name == "is_retracted":
                # Turning on is listed above; turning off is drift.
                changed = bool(before.get(name)) and not record.get(name)
            else:
                changed = record.get(name) != before.get(name)
            if changed:
                delta.field_counts[name] += 1
    return delta


def _describe(record: Record) -> str:
    """One bullet for a listed work, carrying the audit signal."""
    tracked = _tracked(record)
    others = [a.get("name") or "?" for a in record.get("authors") or [] if not a.get("tracked")]
    bits = [str(record.get("year") or "no year")]
    if record.get("venue"):
        bits.append(str(record["venue"]))
    if record.get("type"):
        bits.append(str(record["type"]))
    if record.get("source") == "manual":
        bits.append("manual entry")
    lines = [f"- **{record.get('title') or '(untitled)'}**", f"  {' · '.join(bits)}"]
    lines.append(f"  Tracked: {', '.join(tracked) if tracked else '**nobody**'}")
    if others:
        shown = ", ".join(others[:MAX_COAUTHORS])
        if len(others) > MAX_COAUTHORS:
            shown += f", +{len(others) - MAX_COAUTHORS} more"
        lines.append(f"  Co-authors: {shown}")
    if record.get("doi"):
        lines.append(f"  {record['doi']}")
    return "\n".join(lines)


def _describe_retracking(item: tuple[Record, list[str]]) -> str:
    record, before = item
    return _describe(record) + f"\n  Previously tracked: {', '.join(before) or 'nobody'}"


def _section(title: str, items: list[Any], describe: Callable[[Any], str]) -> list[str]:
    out = [f"#### {title} ({len(items)})", ""]
    out.extend(describe(item) for item in items[:LISTED_CAP])
    if len(items) > LISTED_CAP:
        out.append(f"\n_{len(items) - LISTED_CAP} more not listed; see the raw diff._")
    out.append("")
    return out


def render_markdown(delta: Delta, warnings: list[str]) -> str:
    """The reviewer's page: headline, the run's warnings, then the sections."""
    headline = delta.headline()
    lines = ["### Publications refresh", "", f"**{headline[0].upper()}{headline[1:]}.**", ""]
    if warnings:
        lines += ["**Warnings**", "", *(f"- {warning}" for warning in warnings), ""]
    if delta.added:
        lines += [
            "> **Check the additions before merging.** Works by a same-name researcher "
            "arrive here and `erga verify` cannot flag them; unfamiliar co-authors or an "
            "off-topic venue is the tell. To drop one, add its DOI or id to your "
            "overrides file with `exclude: true`.",
            "",
        ]
        lines += _section("Added", delta.added, _describe)
    if delta.removed:
        lines += _section("Removed", delta.removed, _describe)
    if delta.retracted:
        lines += _section("Retracted", delta.retracted, _describe)
    if delta.retracked:
        lines += _section("Tracking changed", delta.retracked, _describe_retracking)
    if delta.field_counts:
        lines += ["#### Other changes", "", "| Field | Works affected |", "|---|---|"]
        ranked = sorted(delta.field_counts.items(), key=lambda item: (-item[1], item[0]))
        lines += [f"| `{name}` | {count} |" for name, count in ranked]
        lines += ["", "_Metadata drift from OpenAlex. Nothing to action._", ""]
    if delta.tag_changes:
        lines += [
            "#### Curation",
            "",
            f"Tags changed on {_plural(delta.tag_changes, 'work')}, from your tags file. "
            "Manual entries are marked as such in the lists above.",
            "",
        ]
    return "\n".join(lines).rstrip("\n") + "\n"
