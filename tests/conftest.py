"""Pytest configuration and fixtures."""

import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_text():
    """Sample text for testing."""
    return """
    这是一段测试文本。

    第一段落的内容。
    第二段落的内容。

    第三段落，包含更多详细信息。
    """


@pytest.fixture
def sample_long_text():
    """Long sample text for chunking tests."""
    sentences = [
        "这是第一个句子。",
        "这是第二个句子。",
        "这是第三个句子，包含更多内容。",
        "这是第四个句子。",
        "这是第五个句子，也是最后一个。",
    ]
    return " ".join([s * 20 for s in sentences])
