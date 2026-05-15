"""Markdown document parser."""

from pathlib import Path
from typing import Dict, Any
import re


class MarkdownParser(BaseParser):
    """Parser for Markdown documents."""

    SUPPORTED_EXTENSIONS = [".md", ".markdown"]

    def parse(self, file_path: str | Path) -> str:
        """Extract text content from a Markdown file."""
        file_path = Path(file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        return self._clean_markdown(content)

    def _clean_markdown(self, text: str) -> str:
        """Clean Markdown syntax while preserving text content."""
        text = re.sub(r"```[\s\S]*?```", "", text)
        text = re.sub(r"`[^`]+`", "", text)
        text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"[*_]{1,2}([^*_]+)[*_]{1,2}", r"\1", text)
        text = re.sub(r"^\s*[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

        return text.strip()

    def get_metadata(self, file_path: str | Path) -> Dict[str, Any]:
        """Extract metadata from a Markdown file."""
        file_path = Path(file_path)

        metadata = {
            "title": file_path.stem,
            "lines": 0,
            "word_count": 0,
        }

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")
        metadata["lines"] = len(lines)
        metadata["word_count"] = len(content.split())

        title_match = re.match(r"^#\s+(.+)$", content)
        if title_match:
            metadata["title"] = title_match.group(1)

        return metadata
