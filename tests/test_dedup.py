"""Dedup rules; these cases double as documentation of the ranking."""

from __future__ import annotations

from erga.dedup import cluster_by_title, dedup_by_doi, normalize_title
from erga.model import Work


def test_normalize_title_folds_accents_dashes_punctuation() -> None:
    assert normalize_title("Naïve–Bayes:  Methods!") == "naive bayes methods"  # noqa: RUF001
    assert normalize_title("HIGH‐ENERGY metaphysics") == "high energy metaphysics"  # noqa: RUF001
    assert normalize_title("  ") == ""


def test_doi_dedup_is_case_insensitive_and_inherits() -> None:
    a = Work(id="W1", title="A", doi="https://doi.org/10.5555/ABC", cited_by_count=10)
    b = Work(
        id="W2",
        title="A (repository copy)",
        doi="https://doi.org/10.5555/abc",
        abstract="An abstract.",
        open_access_url="https://repo.example/pdf",
    )
    kept = dedup_by_doi([a, b])
    assert [w.id for w in kept] == ["W1"]
    assert kept[0].abstract == "An abstract."
    assert kept[0].open_access_url == "https://repo.example/pdf"


def test_doi_dedup_manual_wins() -> None:
    openalex = Work(id="W1", title="A", doi="https://doi.org/10.5555/abc", cited_by_count=99)
    manual = Work(id="manual-a", title="A", doi="https://doi.org/10.5555/ABC", source="manual")
    assert [w.id for w in dedup_by_doi([openalex, manual])] == ["manual-a"]


def test_works_without_doi_pass_through_doi_dedup() -> None:
    works = [Work(id="W1", title="A"), Work(id="W2", title="B")]
    assert len(dedup_by_doi(works)) == 2


def test_title_cluster_version_of_record_beats_cited_preprint() -> None:
    journal = Work(
        id="W2",
        title="A Long Enough Title Here",
        doi="https://doi.org/10.5555/vor",
        cited_by_count=2,
    )
    arxiv = Work(
        id="W1",
        title="A Long Enough Title Here",
        doi="https://doi.org/10.48550/arXiv.2401.00001",
        cited_by_count=100,
    )
    preprint_type = Work(
        id="W3",
        title="A Long Enough Title Here",
        doi="https://doi.org/10.5555/other",
        type="preprint",
        cited_by_count=500,
    )
    kept = cluster_by_title([journal, arxiv, preprint_type])
    assert [w.id for w in kept] == ["W2"]


def test_title_cluster_has_doi_then_citations_then_newest() -> None:
    no_doi = Work(id="W1", title="Another Sufficiently Long Title")
    low_cited = Work(
        id="W2", title="Another Sufficiently Long Title", doi="https://doi.org/10.5555/a"
    )
    high_cited = Work(
        id="W3",
        title="Another Sufficiently Long Title",
        doi="https://doi.org/10.5555/b",
        cited_by_count=5,
    )
    assert [w.id for w in cluster_by_title([no_doi, low_cited, high_cited])] == ["W3"]

    # Newest OpenAlex record wins the final tie — numerically, so W10 beats
    # W9 despite sorting before it as a string. Dates deliberately do not
    # participate: deposit versions carry later dates than the version of
    # record.
    older = Work(id="W9", title="Dated Sufficiently Long Title", date="2021-06-01")
    newer = Work(id="W10", title="Dated Sufficiently Long Title", date="2020-01-01")
    assert [w.id for w in cluster_by_title([older, newer])] == ["W10"]
    assert [w.id for w in cluster_by_title([newer, older])] == ["W10"]


def test_repository_prefixes_include_institutional_repositories() -> None:
    publica = Work(
        id="W1",
        title="Institutional Copy of a Sufficiently Long Title",
        doi="https://doi.org/10.24406/publica-7036",
    )
    journal = Work(
        id="W2",
        title="Institutional Copy of a Sufficiently Long Title",
        doi="https://doi.org/10.1016/j.bdr.2025.100575",
    )
    assert [w.id for w in cluster_by_title([publica, journal])] == ["W2"]


def test_short_titles_bypass_clustering() -> None:
    works = [Work(id="W1", title="Editorial"), Work(id="W2", title="Editorial")]
    assert len(cluster_by_title(works)) == 2


def test_datasets_never_merge_with_papers() -> None:
    paper = Work(id="W1", title="Psychoceramics Survey Twenty Twenty-Two")
    dataset = Work(id="W2", title="Psychoceramics Survey Twenty Twenty-Two", type="dataset")
    assert len(cluster_by_title([paper, dataset])) == 2


def test_keep_distinct_bypasses_clustering() -> None:
    a = Work(id="W1", title="Annual Report on Pot Integrity")
    b = Work(id="W2", title="Annual Report on Pot Integrity", keep_distinct=True)
    assert len(cluster_by_title([a, b])) == 2


def test_cluster_winner_inherits_abstract_and_oa() -> None:
    winner = Work(id="W1", title="Inheritance Sufficiently Long Title", cited_by_count=10)
    absorbed = Work(
        id="W2",
        title="Inheritance Sufficiently Long Title",
        abstract="From the copy.",
        open_access_url="https://oa.example/pdf",
    )
    kept = cluster_by_title([winner, absorbed])
    assert kept[0].id == "W1"
    assert kept[0].abstract == "From the copy."
    assert kept[0].open_access_url == "https://oa.example/pdf"
