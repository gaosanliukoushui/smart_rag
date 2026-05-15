"""Unit tests for embedding service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.embedding_service import EmbeddingService


class TestEmbeddingService:
    """Tests for EmbeddingService."""

    @pytest.mark.asyncio
    async def test_embed_query(self):
        """Test embedding a single query."""
        service = EmbeddingService(dimension=4)

        with patch.object(service, "load_model", new_callable=AsyncMock):
            with patch("app.services.embedding_service.SentenceTransformer") as mock_st:
                mock_model = MagicMock()
                mock_model.encode.return_value = [[0.1, 0.2, 0.3, 0.4]]
                mock_st.return_value = mock_model

                service._model = mock_model
                result = await service.embed_query("test query")

                assert len(result) == 4

    @pytest.mark.asyncio
    async def test_embed_multiple(self):
        """Test embedding multiple texts."""
        service = EmbeddingService(dimension=4)

        with patch.object(service, "load_model", new_callable=AsyncMock):
            with patch("app.services.embedding_service.SentenceTransformer") as mock_st:
                mock_model = MagicMock()
                mock_model.encode.return_value = [[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]]
                mock_st.return_value = mock_model

                service._model = mock_model
                result = await service.embed(["text1", "text2"])

                assert len(result) == 2
                assert len(result[0]) == 4
