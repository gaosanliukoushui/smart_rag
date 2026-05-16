"""Parsers package for document parsing."""

from pathlib import Path
from typing import Dict, Type

from app.parsers.base import BaseParser
from app.parsers.pdf_parser import PDFParser
from app.parsers.markdown_parser import MarkdownParser
from app.parsers.word_parser import WordParser
from app.parsers.text_parser import TextParser


PARSERS: Dict[str, Type[BaseParser]] = {
    ".pdf": PDFParser,
    ".md": MarkdownParser,
    ".markdown": MarkdownParser,
    ".docx": WordParser,
    ".txt": TextParser,
    ".text": TextParser,
}


def get_parser(file_path: str | Path) -> BaseParser:
    """Get the appropriate parser for a file based on its extension.

    Args:
        file_path: Path to the document file

    Returns:
        An instance of the appropriate parser

    Raises:
        ValueError: If the file type is not supported
    """
    ext = Path(file_path).suffix.lower()
    parser_cls = PARSERS.get(ext)
    if not parser_cls:
        supported = ", ".join(PARSERS.keys())
        raise ValueError(f"Unsupported file type: '{ext}'. Supported types: {supported}")
    return parser_cls()


def get_supported_extensions() -> list:
    """Return list of all supported file extensions."""
    return list(PARSERS.keys())
