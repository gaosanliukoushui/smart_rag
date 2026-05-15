"""Unit tests for parsers."""

import pytest
from pathlib import Path
import tempfile

from app.parsers.text_parser import TextParser
from app.parsers.markdown_parser import MarkdownParser


class TestTextParser:
    """Tests for TextParser."""

    def test_parse_basic(self, temp_dir, sample_text):
        """Test basic text parsing."""
        file_path = temp_dir / "test.txt"
        file_path.write_text(sample_text, encoding="utf-8")

        parser = TextParser()
        result = parser.parse(file_path)

        assert "测试文本" in result
        assert "第一段落" in result

    def test_get_metadata(self, temp_dir, sample_text):
        """Test metadata extraction."""
        file_path = temp_dir / "test.txt"
        file_path.write_text(sample_text, encoding="utf-8")

        parser = TextParser()
        metadata = parser.get_metadata(file_path)

        assert metadata["title"] == "test"
        assert "lines" in metadata
        assert "word_count" in metadata


class TestMarkdownParser:
    """Tests for MarkdownParser."""

    def test_parse_basic(self, temp_dir):
        """Test basic markdown parsing."""
        content = """# Title

This is a paragraph.

## Section

Another paragraph.
"""
        file_path = temp_dir / "test.md"
        file_path.write_text(content, encoding="utf-8")

        parser = MarkdownParser()
        result = parser.parse(file_path)

        assert "Title" in result
        assert "paragraph" in result
        assert "#" not in result

    def test_get_metadata(self, temp_dir):
        """Test markdown metadata extraction."""
        content = """# Document Title

Some content.
"""
        file_path = temp_dir / "test.md"
        file_path.write_text(content, encoding="utf-8")

        parser = MarkdownParser()
        metadata = parser.get_metadata(file_path)

        assert metadata["title"] == "Document Title"
        assert metadata["lines"] > 0
