"""The author-disambiguation report.

OpenAlex author identities split and conflate people, so this is a
first-class feature: it shows what each configured author actually resolves
to before a build trusts those ids.
"""

from __future__ import annotations

from erga.config import AuthorConfig, Config
from erga.dedup import normalize_title
from erga.openalex import AuthorProfile, OpenAlexClient

IMPLAUSIBLE_WORKS_COUNT = 2000
RECENT_TITLES = 3
MAX_NAME_VARIANTS = 5
MAX_SAME_NAME = 5


def _name_tokens(name: str) -> set[str]:
    """Comparable word tokens: accents and punctuation folded, initials dropped.

    Names want the same text folding titles do, so dedup's normalizer is the
    single owner of that logic.
    """
    return {t for t in normalize_title(name).split() if len(t) >= 2}


def _looks_like(profile: AuthorProfile, author: AuthorConfig) -> bool:
    """Whether a profile's names plausibly belong to the configured author.

    Sharing one full word (never a bare initial) between any profile name and
    the configured name or aliases counts. Errs toward flagging: a
    transliteration mismatch is a cheap false alarm in a report a human is
    reading, while a stranger's profile fetched silently is the failure this
    report exists to prevent.
    """
    configured: set[str] = set()
    for name in [author.name, *author.aliases]:
        configured |= _name_tokens(name)
    return any(
        _name_tokens(candidate) & configured
        for candidate in [profile.display_name, *profile.alternatives]
    )


def _same_name_lines(
    client: OpenAlexClient, author: AuthorConfig, known_ids: set[str]
) -> list[str]:
    """Profiles a name search surfaces beyond the configured/resolved ids.

    These are what a configured id can never show: homonyms, and conflated
    profiles that hold works OpenAlex misassigned. Informational, not
    warnings: same-name strangers are common and only a human can judge them.
    """
    profiles, total = client.search_authors(author.name)
    others = [p for p in profiles if p.id not in known_ids]
    lines = [
        f"  same name, not configured: {p.id}  {p.display_name} — {p.works_count} works"
        for p in others[:MAX_SAME_NAME]
    ]
    # Matches beyond the fetched page, plus fetched ones past the display cap.
    unshown = (total - len(profiles)) + len(others[MAX_SAME_NAME:])
    if unshown > 0:
        lines.append(f"  … and {unshown} more name match(es) on OpenAlex")
    return lines


def verify_report(config: Config, client: OpenAlexClient) -> tuple[str, list[str]]:
    """Human-readable report plus a list of warnings."""
    lines: list[str] = []
    warnings: list[str] = []
    for author in config.authors:
        if author.tracking_only:
            lines.append(f"{author.name} (no ids; tracked by name only, nothing fetched)")
            lines.extend(_same_name_lines(client, author, set()))
            lines.append("")
            continue
        identity = author.orcid or author.openalex_id or ""
        lines.append(f"{author.name} ({identity})")
        resolved = client.resolve_author(author)
        strangers = [p for p in resolved.profiles if not _looks_like(p, author)]

        if not resolved.profiles:
            lines.append("  resolved to no OpenAlex author")
            warnings.append(f"{author.name}: resolves to no OpenAlex author id")
        # The ORCID warnings judge only the profiles the ORCID resolved to: a
        # profile contributed by a pinned openalex_id says nothing about the
        # iD, and blaming the orcid for a mistyped pin inverts the advice.
        orcid_profiles = resolved.orcid_profiles
        orcid_strangers = [p for p in orcid_profiles if not _looks_like(p, author)]
        reported: list[AuthorProfile] = []
        if len(orcid_profiles) > 1:
            total = max(resolved.orcid_profile_total, len(orcid_profiles))
            if orcid_strangers:
                example = orcid_strangers[0].display_name or orcid_strangers[0].id
                warnings.append(
                    f"{author.name}: ORCID is carried by {total} author profiles that "
                    f"look like different people (e.g. {example!r}); fetching would pull "
                    f"strangers' works — remove the orcid and pin openalex_id instead"
                )
                reported = orcid_strangers
            else:
                warnings.append(
                    f"{author.name}: ORCID resolves to {total} author ids "
                    f"(split profile; consider pinning openalex_id)"
                )
        for stranger in [p for p in strangers if p not in reported]:
            warnings.append(
                f"{author.name}: resolves to {stranger.display_name!r}, which does "
                f"not look like the configured name (mistyped orcid or openalex_id?)"
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
        lines.extend(_same_name_lines(client, author, set(resolved.ids)))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n", warnings
