"""
Stripe documentation ingestion pipeline.

Pipeline stages:
1. Load — Read markdown files from backend/data/docs/stripe/
2. Chunk — Semantic splitting on headers + recursive character splitting
3. Enrich — Contextual Retrieval: prepend contextual description via Claude Haiku
4. Embed & Store — Voyage AI embeddings into ChromaDB
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from app.config import get_settings
from app.rag.vectorstore import add_documents

logger = logging.getLogger(__name__)

_DOCS_DIR = Path(__file__).resolve().parents[2] / "data" / "docs" / "stripe"

# Complexity mapping from header depth
_COMPLEXITY_MAP: dict[int, str] = {
    1: "overview",
    2: "concept",
    3: "detail",
}


class StripeDocLoader:
    """Reads markdown files from the Stripe docs directory."""

    def __init__(self, docs_dir: Path = _DOCS_DIR) -> None:
        self.docs_dir = docs_dir

    def load(self) -> list[Document]:
        """Load all markdown files and return Documents with metadata."""
        documents: list[Document] = []
        md_files = sorted(self.docs_dir.glob("*.md"))

        if not md_files:
            logger.warning("No markdown files found in %s", self.docs_dir)
            return documents

        for filepath in md_files:
            raw = filepath.read_text(encoding="utf-8")
            metadata = self._extract_frontmatter(raw, filepath)
            content = self._strip_frontmatter(raw)
            documents.append(
                Document(page_content=content, metadata=metadata)
            )
            logger.info("Loaded %s (%d chars)", filepath.name, len(content))

        logger.info(
            "Loaded %d documents from %s", len(documents), self.docs_dir
        )
        return documents

    @staticmethod
    def _extract_frontmatter(raw: str, filepath: Path) -> dict[str, str]:
        """Extract metadata from HTML comment frontmatter block."""
        metadata: dict[str, str] = {
            "source_file": filepath.name,
            "product": "stripe",
        }
        match = re.search(r"<!--\s*(.*?)\s*-->", raw, re.DOTALL)
        if match:
            block = match.group(1)
            for line in block.strip().splitlines():
                line = line.strip()
                if ":" in line:
                    key, _, value = line.partition(":")
                    metadata[key.strip()] = value.strip()
        return metadata

    @staticmethod
    def _strip_frontmatter(raw: str) -> str:
        """Remove the leading frontmatter comment from content."""
        return re.sub(
            r"^<!--.*?-->\s*", "", raw, count=1, flags=re.DOTALL
        ).strip()


class SemanticChunker:
    """Two-pass semantic chunker.

    Pass 1: MarkdownHeaderTextSplitter splits on h1/h2/h3
    Pass 2: RecursiveCharacterTextSplitter for size limits
    """

    _HEADERS_TO_SPLIT = [
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
    ]

    def __init__(
        self, chunk_size: int = 1000, chunk_overlap: int = 200
    ) -> None:
        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self._HEADERS_TO_SPLIT,
            strip_headers=False,
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk(self, documents: list[Document]) -> list[Document]:
        """Split documents into enriched chunks with full metadata."""
        all_chunks: list[Document] = []

        for doc in documents:
            doc_meta = doc.metadata
            header_chunks = self.header_splitter.split_text(
                doc.page_content
            )
            h2_sections = self._extract_h2_sections(doc.page_content)

            chunk_index = 0
            for hchunk in header_chunks:
                section_path = self._build_section_path(hchunk.metadata)
                complexity = self._infer_complexity(hchunk.metadata)
                parent_section = self._find_parent_section(
                    section_path, h2_sections
                )

                sub_chunks = self.text_splitter.split_text(
                    hchunk.page_content
                )

                for text in sub_chunks:
                    chunk_meta = {
                        **doc_meta,
                        "chunk_index": chunk_index,
                        "source_url": doc_meta.get("url", ""),
                        "section_path": section_path,
                        "complexity": complexity,
                        "parent_section": parent_section,
                    }
                    all_chunks.append(
                        Document(page_content=text, metadata=chunk_meta)
                    )
                    chunk_index += 1

        logger.info(
            "Created %d chunks from %d documents",
            len(all_chunks), len(documents),
        )
        return all_chunks

    @staticmethod
    def _build_section_path(header_meta: dict[str, str]) -> str:
        """Build section path like 'Auth > API Keys > Restricted'."""
        parts: list[str] = []
        for level in ("h1", "h2", "h3"):
            if level in header_meta:
                parts.append(header_meta[level])
        return " > ".join(parts) if parts else "Root"

    @staticmethod
    def _infer_complexity(header_meta: dict[str, str]) -> str:
        """Infer complexity from deepest header level present."""
        depth = 1
        if "h3" in header_meta:
            depth = 3
        elif "h2" in header_meta:
            depth = 2
        return _COMPLEXITY_MAP.get(depth, "overview")

    @staticmethod
    def _extract_h2_sections(content: str) -> dict[str, str]:
        """Extract full text of each h2 section for parent context."""
        sections: dict[str, str] = {}
        parts = re.split(r"(?=^## )", content, flags=re.MULTILINE)
        for part in parts:
            match = re.match(r"^## (.+)", part)
            if match:
                header = match.group(1).strip()
                sections[header] = part.strip()
        return sections

    @staticmethod
    def _find_parent_section(
        section_path: str, h2_sections: dict[str, str]
    ) -> str:
        """Find the h2 parent section text for enrichment."""
        parts = section_path.split(" > ")
        if len(parts) >= 2:
            h2_name = parts[1]
            if h2_name in h2_sections:
                return h2_sections[h2_name][:2000]
        for name, text in h2_sections.items():
            if name in section_path:
                return text[:2000]
        return ""


class ContextualEnricher:
    """Enriches chunks using Anthropic's Contextual Retrieval technique.

    Calls Claude Haiku to generate a 2-3 sentence contextual prefix
    that situates each chunk within its broader document section.
    """

    _PROMPT_TEMPLATE = (
        "<document>\n{parent_section_text}\n</document>\n\n"
        "<chunk>\n{chunk_text}\n</chunk>\n\n"
        "Provide a concise 2-3 sentence contextual description that "
        "situates this chunk within the broader document. What product "
        "feature, API, or concept does it cover? How does it relate to "
        'its parent section? Start with "This chunk..."'
    )

    def __init__(self, batch_size: int = 5) -> None:
        settings = get_settings()
        self._llm = ChatAnthropic(
            model=settings.fast_model,
            api_key=settings.anthropic_api_key,
            max_tokens=200,
            temperature=0.0,
        )
        self._batch_size = batch_size

    async def enrich(self, chunks: list[Document]) -> list[Document]:
        """Add contextual prefixes to all chunks."""
        enriched: list[Document] = []
        total = len(chunks)

        for i, chunk in enumerate(chunks):
            original_content = chunk.page_content
            parent_section = chunk.metadata.get("parent_section", "")

            try:
                context_prefix = await self._generate_context(
                    chunk_text=original_content,
                    parent_section_text=parent_section or original_content[:500],
                )
                enriched_content = f"{context_prefix}\n\n{original_content}"
            except Exception as e:
                logger.warning(
                    "Enrichment failed for chunk %d: %s. Using original.",
                    i, str(e),
                )
                enriched_content = original_content
                context_prefix = ""

            meta = {
                k: v
                for k, v in chunk.metadata.items()
                if k != "parent_section"
            }
            meta["original_content"] = original_content
            meta["context_prefix"] = context_prefix

            enriched.append(
                Document(page_content=enriched_content, metadata=meta)
            )

            if (i + 1) % 10 == 0 or i == total - 1:
                logger.info("Enriched %d/%d chunks", i + 1, total)

        return enriched

    async def _generate_context(
        self, chunk_text: str, parent_section_text: str
    ) -> str:
        """Call Claude Haiku to generate the contextual prefix."""
        prompt = self._PROMPT_TEMPLATE.format(
            parent_section_text=parent_section_text,
            chunk_text=chunk_text,
        )
        response = await self._llm.ainvoke(prompt)
        return response.content.strip()


async def run_ingestion(
    product: str = "stripe",
    skip_enrichment: bool = False,
) -> dict[str, Any]:
    """Orchestrate the full ingestion pipeline.

    Load → Chunk → Enrich → Store in ChromaDB.
    """
    stats: dict[str, Any] = {"product": product}

    # Stage 1: Load
    logger.info("=== Stage 1: Loading %s documents ===", product)
    loader = StripeDocLoader()
    documents = loader.load()
    stats["documents_loaded"] = len(documents)

    if not documents:
        logger.error("No documents found — aborting ingestion")
        return stats

    # Stage 2: Chunk
    logger.info("=== Stage 2: Semantic chunking ===")
    settings = get_settings()
    chunker = SemanticChunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = chunker.chunk(documents)
    stats["chunks_created"] = len(chunks)

    # Stage 3: Enrich
    if skip_enrichment:
        logger.info("=== Stage 3: Skipping enrichment ===")
        for chunk in chunks:
            chunk.metadata["original_content"] = chunk.page_content
            chunk.metadata["context_prefix"] = ""
            chunk.metadata.pop("parent_section", None)
        enriched = chunks
    else:
        logger.info("=== Stage 3: Contextual enrichment ===")
        enricher = ContextualEnricher()
        enriched = await enricher.enrich(chunks)
    stats["chunks_enriched"] = len(enriched)

    # Stage 4: Store in ChromaDB
    logger.info("=== Stage 4: Storing in ChromaDB ===")
    stored = add_documents(product, enriched)
    stats["chunks_stored"] = stored

    logger.info("=== Ingestion complete ===")
    logger.info("Stats: %s", stats)
    return stats
