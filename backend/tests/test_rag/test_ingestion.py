"""Tests for the document ingestion pipeline components."""

from pathlib import Path

from langchain_core.documents import Document

from app.rag.ingestion import ContextualEnricher, SemanticChunker, StripeDocLoader

# ── StripeDocLoader Tests ────────────────────────────────────────────


class TestStripeDocLoaderMetadata:
    def test_frontmatter_with_all_fields(self):
        raw = (
            "<!--\ntitle: Payments\nurl: https://docs.stripe.com/payments\n"
            "topic: payments\ncomplexity: intermediate\n-->\n# Payments"
        )
        meta = StripeDocLoader._extract_frontmatter(raw, Path("payments.md"))
        assert meta["title"] == "Payments"
        assert meta["url"] == "https://docs.stripe.com/payments"
        assert meta["topic"] == "payments"
        assert meta["complexity"] == "intermediate"
        assert meta["product"] == "stripe"
        assert meta["source_file"] == "payments.md"

    def test_frontmatter_missing_block(self):
        """Documents without frontmatter still get base metadata."""
        raw = "# No Frontmatter\n\nJust content."
        meta = StripeDocLoader._extract_frontmatter(raw, Path("test.md"))
        assert meta["source_file"] == "test.md"
        assert meta["product"] == "stripe"
        assert "title" not in meta

    def test_strip_frontmatter_removes_comment(self):
        raw = "<!--\ntitle: Test\n-->\n# Content"
        content = StripeDocLoader._strip_frontmatter(raw)
        assert content == "# Content"

    def test_strip_frontmatter_no_comment(self):
        raw = "# No Comment\n\nContent."
        content = StripeDocLoader._strip_frontmatter(raw)
        assert content == raw


class TestStripeDocLoaderFiles:
    def test_load_multiple_files(self, tmp_path):
        for i in range(3):
            doc = (
                f"<!--\ntitle: Doc{i}\nurl: https://example.com/{i}\n"
                f"topic: t{i}\n-->\n# Doc {i}\nContent {i}."
            )
            (tmp_path / f"doc{i}.md").write_text(doc)

        loader = StripeDocLoader(docs_dir=tmp_path)
        docs = loader.load()
        assert len(docs) == 3
        # Sorted by filename
        titles = [d.metadata["title"] for d in docs]
        assert titles == ["Doc0", "Doc1", "Doc2"]

    def test_load_ignores_non_markdown(self, tmp_path):
        (tmp_path / "doc.md").write_text("<!--\ntitle: MD\n-->\n# MD")
        (tmp_path / "notes.txt").write_text("not markdown")
        (tmp_path / "data.json").write_text("{}")

        loader = StripeDocLoader(docs_dir=tmp_path)
        docs = loader.load()
        assert len(docs) == 1

    def test_load_empty_directory(self, tmp_path):
        loader = StripeDocLoader(docs_dir=tmp_path)
        docs = loader.load()
        assert docs == []


# ── SemanticChunker Tests ────────────────────────────────────────────


class TestSemanticChunkerDetails:
    def test_chunk_respects_size_limits(self):
        chunker = SemanticChunker(chunk_size=500, chunk_overlap=50)
        doc = Document(
            page_content="## Section\n\n" + ("Word " * 200),
            metadata={"product": "stripe", "url": "https://example.com", "topic": "test"},
        )
        chunks = chunker.chunk([doc])
        for c in chunks:
            # Allow 2x chunk_size as upper bound due to overlap
            assert len(c.page_content) <= 1000

    def test_section_path_from_headers(self):
        meta = {"h1": "Auth", "h2": "API Keys", "h3": "Restricted"}
        path = SemanticChunker._build_section_path(meta)
        assert path == "Auth > API Keys > Restricted"

    def test_section_path_h1_only(self):
        meta = {"h1": "Overview"}
        path = SemanticChunker._build_section_path(meta)
        assert path == "Overview"

    def test_section_path_empty(self):
        path = SemanticChunker._build_section_path({})
        assert path == "Root"

    def test_complexity_h3_is_detail(self):
        assert SemanticChunker._infer_complexity({"h1": "A", "h2": "B", "h3": "C"}) == "detail"

    def test_complexity_h2_is_concept(self):
        assert SemanticChunker._infer_complexity({"h1": "A", "h2": "B"}) == "concept"

    def test_complexity_h1_only_is_overview(self):
        assert SemanticChunker._infer_complexity({"h1": "A"}) == "overview"

    def test_complexity_no_headers_is_overview(self):
        assert SemanticChunker._infer_complexity({}) == "overview"

    def test_extract_h2_sections(self):
        content = "# Title\n\n## Section A\n\nContent A.\n\n## Section B\n\nContent B."
        sections = SemanticChunker._extract_h2_sections(content)
        assert "Section A" in sections
        assert "Section B" in sections

    def test_find_parent_section_by_path(self):
        h2_sections = {"API Keys": "Full API keys section text here."}
        result = SemanticChunker._find_parent_section("Auth > API Keys > Restricted", h2_sections)
        assert result == "Full API keys section text here."

    def test_find_parent_section_no_match(self):
        h2_sections = {"Payments": "Payment section text."}
        result = SemanticChunker._find_parent_section("Auth > Unknown", h2_sections)
        assert result == ""

    def test_find_parent_section_partial_match(self):
        h2_sections = {"Auth": "Auth section text."}
        result = SemanticChunker._find_parent_section("Root > Auth", h2_sections)
        assert "Auth section text" in result


# ── ContextualEnricher Tests ─────────────────────────────────────────


class TestContextualEnricherPrompt:
    def test_prompt_template_format(self):
        """The prompt template has required placeholders."""
        template = ContextualEnricher._PROMPT_TEMPLATE
        assert "{parent_section_text}" in template
        assert "{chunk_text}" in template
        assert "<document>" in template
        assert "<chunk>" in template
