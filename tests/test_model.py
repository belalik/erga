from __future__ import annotations

from erga.model import Work, WorkAuthor, doi_key, doi_url, slugify


def test_doi_key_strips_host_and_case() -> None:
    assert doi_key("https://doi.org/10.5555/ABC") == "10.5555/abc"
    assert doi_key("http://dx.doi.org/10.5555/xyz") == "10.5555/xyz"
    assert doi_key("10.5555/AbC") == "10.5555/abc"


def test_doi_url_from_bare_and_url_forms() -> None:
    assert doi_url("10.5555/abc") == "https://doi.org/10.5555/abc"
    assert doi_url("https://doi.org/10.5555/ABC") == "https://doi.org/10.5555/abc"


def test_slugify() -> None:
    assert slugify("Toward a Unified Theory!") == "toward-a-unified-theory"
    assert slugify("Café: Décor & Design") == "cafe-decor-design"
    assert slugify("!!!") == "untitled"


def test_slugify_caps_length() -> None:
    assert len(slugify("word " * 40)) <= 60


def test_to_json_key_order_and_shapes() -> None:
    work = Work(
        id="W1",
        title="T",
        authors=[WorkAuthor(name="A", orcid=None, tracked=True)],
        open_access_url="https://example.org/paper.pdf",
    )
    data = work.to_json()
    assert list(data) == [
        "id",
        "title",
        "authors",
        "year",
        "date",
        "venue",
        "type",
        "doi",
        "cited_by_count",
        "abstract",
        "open_access",
        "tags",
        "is_retracted",
        "source",
    ]
    assert data["open_access"] == {"url": "https://example.org/paper.pdf"}
    assert data["authors"] == [{"name": "A", "orcid": None, "tracked": True, "tracked_as": None}]
    assert "keep_distinct" not in data


def test_to_json_null_open_access() -> None:
    assert Work(id="W1", title="T").to_json()["open_access"] is None
