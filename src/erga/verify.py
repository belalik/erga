"""The author-disambiguation report.

OpenAlex author identities split and conflate people, so this is a
first-class feature: it shows what each configured author actually resolves
to before a build trusts those ids.
"""

from __future__ import annotations

from erga.config import Config
from erga.openalex import OpenAlexClient

IMPLAUSIBLE_WORKS_COUNT = 2000
RECENT_TITLES = 3
MAX_NAME_VARIANTS = 5


def verify_report(config: Config, client: OpenAlexClient) -> tuple[str, list[str]]:
    """Human-readable report plus a list of warnings."""
    lines: list[str] = []
    warnings: list[str] = []
    for author in config.authors:
        identity = author.orcid or author.openalex_id or ""
        lines.append(f"{author.name} ({identity})")
        resolved = client.resolve_author(author)

        if not resolved.profiles:
            lines.append("  resolved to no OpenAlex author")
            warnings.append(f"{author.name}: resolves to no OpenAlex author id")
        if author.orcid and len(resolved.profiles) > 1:
            warnings.append(
                f"{author.name}: ORCID resolves to {len(resolved.profiles)} author ids "
                f"(split profile; consider pinning openalex_id)"
            )

        total_works = 0
        for profile in resolved.profiles:
            total_works += profile.works_count
            lines.append(f"  {profile.id}  {profile.display_name} — {profile.works_count} works")
            if profile.alternatives:
                variants = "; ".join(profile.alternatives[:MAX_NAME_VARIANTS])
                lines.append(f"    also known as: {variants}")
            for raw in client.recent_works(profile.id, RECENT_TITLES):
                title = raw.get("title") or "(untitled)"
                year = raw.get("publication_year")
                lines.append(f"    recent: {title} ({year})")
            if profile.works_count > IMPLAUSIBLE_WORKS_COUNT:
                warnings.append(
                    f"{author.name}: profile {profile.id} has {profile.works_count} works "
                    f"(implausibly many; possibly conflated with another person)"
                )
        if resolved.profiles and total_works == 0:
            warnings.append(f"{author.name}: resolved profile(s) have zero works")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n", warnings
