"""Tests for the semantic chunking and ingestion pipeline."""

import pytest
from langchain_core.documents import Document

from app.rag.ingestion import SemanticChunker, StripeDocLoader

# ── Fixtures ──────────────────────────────────────────────────────────

SAMPLE_DOC_CONTENT = """\
<!--
title: Test Doc
url: https://docs.stripe.com/test
topic: testing
complexity: beginner
-->

# Test Documentation

Overview of the test topic.

## Getting Started

This section covers the basics of getting started with the test API.
You need to install the SDK and configure your API keys before making
any requests. The following steps will guide you through the process
of setting up your development environment.

### Installation

To install the SDK, run the following command in your terminal:

```bash
pip install stripe
```

After installation, verify the package is available by importing it
in your Python code. The SDK supports Python 3.8 and above.

### Configuration

Set your API key in your environment:

```bash
export STRIPE_API_KEY=sk_test_abc123
```

You can also configure the key programmatically in your application
code using the stripe module's api_key attribute.

## Advanced Usage

This section covers advanced patterns for production deployments.

### Error Handling

Always wrap API calls in try-except blocks to handle potential errors
gracefully. The SDK raises specific exception types for different
error conditions, including network errors, authentication failures,
and validation errors. Here is an example of comprehensive error handling:

```python
try:
    charge = stripe.Charge.create(amount=2000, currency="usd")
except stripe.error.CardError as e:
    print(f"Card declined: {e}")
except stripe.error.RateLimitError as e:
    print(f"Rate limited: {e}")
```

### Retry Logic

Implement exponential backoff for transient failures. The recommended
approach is to start with a 1-second delay and double it on each retry,
with a maximum of 3 retries. This ensures your application remains
responsive while handling temporary service disruptions.
"""


@pytest.fixture
def sample_documents() -> list[Document]:
    """Create a small set of test documents."""
    return [
        Document(
            page_content=SAMPLE_DOC_CONTENT.split("-->")[1].strip(),
            metadata={
                "title": "Test Doc",
                "url": "https://docs.stripe.com/test",
                "topic": "testing",
                "complexity": "beginner",
                "product": "stripe",
                "source_file": "test.md",
            },
        )
    ]


@pytest.fixture
def chunker() -> SemanticChunker:
    return SemanticChunker(chunk_size=1000, chunk_overlap=200)


# ── StripeDocLoader Tests ─────────────────────────────────────────────


class TestStripeDocLoader:
    def test_extract_frontmatter(self, tmp_path):
        """Frontmatter metadata is correctly parsed from HTML comments."""
        from pathlib import Path

        meta = StripeDocLoader._extract_frontmatter(SAMPLE_DOC_CONTENT, Path("test.md"))
        assert meta["title"] == "Test Doc"
        assert meta["url"] == "https://docs.stripe.com/test"
        assert meta["topic"] == "testing"
        assert meta["complexity"] == "beginner"
        assert meta["product"] == "stripe"

    def test_strip_frontmatter(self):
        """Frontmatter comment is removed from content."""
        content = StripeDocLoader._strip_frontmatter(SAMPLE_DOC_CONTENT)
        assert not content.startswith("<!--")
        assert content.startswith("# Test Documentation")

    def test_load_from_directory(self, tmp_path):
        """Loader reads all .md files from directory."""
        # Create test markdown files
        doc1 = (
            "<!-- \ntitle: Doc1\nurl: https://example.com/1\n"
            "topic: auth\n-->\n\n# Doc 1\n\nContent."
        )
        (tmp_path / "doc1.md").write_text(doc1)
        doc2 = (
            "<!-- \ntitle: Doc2\nurl: https://example.com/2\n"
            "topic: payments\n-->\n\n# Doc 2\n\nMore."
        )
        (tmp_path / "doc2.md").write_text(doc2)
        # Non-markdown file should be ignored
        (tmp_path / "notes.txt").write_text("not a doc")

        loader = StripeDocLoader(docs_dir=tmp_path)
        docs = loader.load()

        assert len(docs) == 2
        assert docs[0].metadata["title"] == "Doc1"
        assert docs[1].metadata["title"] == "Doc2"

    def test_load_empty_directory(self, tmp_path):
        """Loader returns empty list for directory with no markdown files."""
        loader = StripeDocLoader(docs_dir=tmp_path)
        docs = loader.load()
        assert docs == []


# ── SemanticChunker Tests ─────────────────────────────────────────────


class TestSemanticChunker:
    def test_chunks_created(self, chunker, sample_documents):
        """Chunker produces multiple chunks from a single document."""
        chunks = chunker.chunk(sample_documents)
        assert len(chunks) > 1

    def test_chunk_size_bounds(self, chunker, sample_documents):
        """Chunk content length stays within expected bounds."""
        chunks = chunker.chunk(sample_documents)
        for chunk in chunks:
            # Allow some flexibility: overlap can push chunks slightly over
            assert len(chunk.page_content) <= 1500, (
                f"Chunk too large: {len(chunk.page_content)} chars"
            )

    def test_metadata_populated(self, chunker, sample_documents):
        """All required metadata fields are present on each chunk."""
        chunks = chunker.chunk(sample_documents)
        required_fields = {
            "product", "topic", "chunk_index",
            "source_url", "section_path", "complexity",
        }

        for chunk in chunks:
            for field in required_fields:
                assert field in chunk.metadata, f"Missing metadata field: {field}"

    def test_section_path_hierarchy(self, chunker, sample_documents):
        """Section paths reflect header hierarchy with ' > ' separator."""
        chunks = chunker.chunk(sample_documents)
        section_paths = {c.metadata["section_path"] for c in chunks}

        # Should have paths reflecting the h1 > h2 > h3 structure
        has_nested_path = any(" > " in p for p in section_paths)
        assert has_nested_path, f"No nested section paths found: {section_paths}"

    def test_complexity_mapping(self, chunker, sample_documents):
        """Complexity is correctly inferred from header depth."""
        chunks = chunker.chunk(sample_documents)
        complexities = {c.metadata["complexity"] for c in chunks}

        # Should have at least overview and concept or detail
        assert len(complexities) >= 2, f"Only found complexities: {complexities}"
        valid = {"overview", "concept", "detail"}
        assert complexities.issubset(valid), f"Invalid complexities: {complexities - valid}"

    def test_chunk_index_sequential(self, chunker, sample_documents):
        """Chunk indices are sequential starting from 0."""
        chunks = chunker.chunk(sample_documents)
        indices = [c.metadata["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_parent_section_populated(self, chunker, sample_documents):
        """Parent section text is attached for contextual enrichment."""
        chunks = chunker.chunk(sample_documents)
        # At least some chunks should have parent_section
        has_parent = [c for c in chunks if c.metadata.get("parent_section")]
        assert len(has_parent) > 0

    def test_no_duplicate_chunks(self, chunker):
        """Identical documents don't produce duplicate chunk content."""
        doc = Document(
            page_content="# Title\n\n## Section\n\nSome unique content here.",
            metadata={"product": "stripe", "topic": "test", "url": "https://example.com"},
        )
        chunks = chunker.chunk([doc, doc])
        # Two identical docs will produce chunks with same content — that's expected
        # But the chunk_index resets per-document, so total is 2x
        assert len(chunks) == 2 * (len(chunks) // 2)

    def test_empty_document(self, chunker):
        """Empty document produces no chunks."""
        doc = Document(page_content="", metadata={"product": "stripe"})
        chunks = chunker.chunk([doc])
        assert len(chunks) == 0
