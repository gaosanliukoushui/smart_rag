"""Base parser interface."""

from abc import ABC, abstractmethod
from typing import Dict, Any
from pathlib import Path


class BaseParser(ABC):
    """Abstract base class for document parsers."""

    SUPPORTED_EXTENSIONS: list = []

    @abstractmethod
    def parse(self, file_path: str | Path) -> str:
        """
        Parse a document and return its text content.

        Args:
            file_path: Path to the document file

        Returns:
            Extracted text content
        """
        pass

    @abstractmethod
    def get_metadata(self, file_path: str | Path) -> Dict[str, Any]:
        """
        Extract metadata from a document.

        Args:
            file_path: Path to the document file

        Returns:
            Dictionary of metadata
        """
        pass

    @classmethod
    def can_parse(cls, file_path: str | Path) -> bool:
        """Check if this parser can handle the given file."""
        ext = Path(file_path).suffix.lower()
        return ext in cls.SUPPORTED_EXTENSIONS
