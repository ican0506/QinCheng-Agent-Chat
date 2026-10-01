from __future__ import annotations

from app.rag.models import RagChunk, RagDocument


class MarkdownPolicyChunker:
    """优先以 Markdown 二级标题作为政策原文的语义边界。"""

    def __init__(self, max_section_length: int = 700) -> None:
        self._max_section_length = max_section_length

    def chunk_documents(self, documents: list[RagDocument]) -> list[RagChunk]:
        return [chunk for document in documents for chunk in self.chunk_document(document)]

    def chunk_document(self, document: RagDocument) -> list[RagChunk]:
        sections = self._sections(document.markdown)
        chunks: list[RagChunk] = []
        for heading, text in sections:
            for index, section_part in enumerate(self._split_section(text), start=1):
                chunks.append(RagChunk(
                    policyId=document.policyId,
                    policyName=document.policyName,
                    region=document.region,
                    department=document.department,
                    sourceUrl=document.sourceUrl,
                    validityStatus=document.validityStatus,
                    lastVerifiedAt=document.lastVerifiedAt,
                    topics=document.topics,
                    targetGroups=document.targetGroups,
                    chunkId=f"{document.policyId}:{len(chunks) + 1}",
                    heading=heading,
                    chunkText=section_part,
                    applicationStatus=document.applicationStatus,
                ))
        return chunks

    @staticmethod
    def _sections(markdown: str) -> list[tuple[str, str]]:
        sections: list[tuple[str, list[str]]] = []
        heading = "概述"
        lines: list[str] = []
        for line in markdown.splitlines():
            if line.startswith("## "):
                if lines:
                    sections.append((heading, lines))
                heading = line[3:].strip()
                lines = []
            elif not line.startswith("# "):
                lines.append(line)
        if lines:
            sections.append((heading, lines))
        return [
            (section_heading, "\n".join(content).strip())
            for section_heading, content in sections
            if "\n".join(content).strip()
        ]

    def _split_section(self, text: str) -> list[str]:
        paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
        parts: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if current and len(current) + len(paragraph) + 2 > self._max_section_length:
                parts.append(current)
                current = ""
            if len(paragraph) > self._max_section_length:
                if current:
                    parts.append(current)
                    current = ""
                parts.extend(
                    paragraph[start:start + self._max_section_length]
                    for start in range(0, len(paragraph), self._max_section_length)
                )
            else:
                current = f"{current}\n\n{paragraph}".strip()
        if current:
            parts.append(current)
        return parts
