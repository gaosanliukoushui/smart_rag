"""Plain text document parser."""

from pathlib import Path
from typing import Dict, Any


class TextParser(BaseParser):
    """Parser for plain text documents."""

    SUPPORTED_EXTENSIONS = [".txt", ".text"]

    def parse(self, file_path: str | Path) -> str:
        """Read plain text content."""
        file_path = Path(file_path)

        encodings = ["utf-8", "gbk", "gb2312", "latin-1"]

        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def get_metadata(self, file_path: str | Path) -> Dict[str, Any]:
        """Extract metadata from a text file."""
        file_path = Path(file_path)
        content = self.parse(file_path)

        return {
            "title": file_path.stem,
            "lines": len(content.split("\n")),
            "word_count": len(content.split()),
            "char_count": len(content),
        }
