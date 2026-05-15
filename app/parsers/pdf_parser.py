"""PDF document parser."""

from pathlib import Path
from typing import Dict, Any

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

from app.parsers.base import BaseParser


class PDFParser(BaseParser):
    """Parser for PDF documents."""

    SUPPORTED_EXTENSIONS = [".pdf"]

    def parse(self, file_path: str | Path) -> str:
        """Extract text content from a PDF file."""
        if not PYPDF_AVAILABLE:
            raise ImportError(
                "pypdf is required for PDF parsing. Install with: pip install pypdf"
            )

        file_path = Path(file_path)
        text_parts = []

        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        return "\n\n".join(text_parts)

    def get_metadata(self, file_path: str | Path) -> Dict[str, Any]:
        """Extract metadata from a PDF file."""
        if not PYPDF_AVAILABLE:
            raise ImportError("pypdf is required for PDF parsing")

        file_path = Path(file_path)
        metadata = {"pages": 0, "title": None, "author": None}

        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            metadata["pages"] = len(reader.pages)

            if reader.metadata:
                metadata["title"] = reader.metadata.get("/Title")
                metadata["author"] = reader.metadata.get("/Author")

        return metadata
