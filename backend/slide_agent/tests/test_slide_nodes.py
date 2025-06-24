"""
Comprehensive test suite for slide agent nodes.

This test suite covers:
- create_presentation_node testing with proper mocking
- generate_titles_node testing with proper mocking
- Compiled graph testing with end-to-end flow
- Error handling and edge cases
- Response format validation

All tests use pytest and follow best practices for async testing.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

from slide_graph.graph import (
    create_presentation_node,
    generate_titles_node,
    graph,
    PresentationState
)
from slide_graph.api.sql_models import PresentationSqlModel


class TestCreatePresentationNode:
    """Test the create_presentation_node function."""

    @pytest.fixture
    def mock_presentation_handler_success(self, mock_presentation_sql_model):
        """Mock successful presentation handler."""
        mock_handler = MagicMock()
        mock_handler.post = AsyncMock(return_value=mock_presentation_sql_model)
        return mock_handler

    @pytest.fixture
    def mock_presentation_handler_failure(self):
        """Mock failed presentation handler."""
        mock_handler = MagicMock()
        mock_handler.post = AsyncMock(
            side_effect=Exception("Database connection failed"))
        return mock_handler

    @pytest.mark.asyncio
    @patch('slide_graph.graph.GeneratePresentationRequirementsHandler')
    @patch('slide_graph.graph.LoggingService')
    @patch('slide_graph.graph.LogMetadata')
    async def test_create_presentation_node_success(
        self,
        mock_log_metadata_cls,
        mock_logging_service_cls,
        mock_handler_cls,
        mock_presentation_state,
        mock_slide_config,
        mock_base_store,
        mock_presentation_handler_success,
        mock_presentation_sql_model,
        mock_logging_service,
        mock_log_metadata
    ):
        """Test successful presentation creation."""

        # Setup mocks
        mock_handler_cls.return_value = mock_presentation_handler_success
        mock_logging_service_cls.return_value = mock_logging_service
        mock_log_metadata_cls.return_value = mock_log_metadata

        # Execute the function
        result = await create_presentation_node(
            mock_presentation_state,
            mock_slide_config,
            store=mock_base_store
        )

        # Assertions
        assert "presentation_id" in result
        assert result["presentation_id"] is not None
        assert len(result["presentation_id"]) == 36  # UUID length
        assert "presentation" in result
        assert result["presentation"] == mock_presentation_sql_model
        assert "error" in result
        assert result["error"] is None

        # Verify handler was called correctly
        mock_handler_cls.assert_called_once()
        mock_presentation_handler_success.post.assert_called_once_with(
            mock_logging_service, mock_log_metadata
        )

    @pytest.mark.asyncio
    @patch('slide_graph.graph.GeneratePresentationRequirementsHandler')
    @patch('slide_graph.graph.LoggingService')
    @patch('slide_graph.graph.LogMetadata')
    async def test_create_presentation_node_failure(
        self,
        mock_log_metadata_cls,
        mock_logging_service_cls,
        mock_handler_cls,
        mock_presentation_state,
        mock_slide_config,
        mock_base_store,
        mock_presentation_handler_failure,
        mock_logging_service,
        mock_log_metadata
    ):
        """Test presentation creation failure."""

        # Setup mocks
        mock_handler_cls.return_value = mock_presentation_handler_failure
        mock_logging_service_cls.return_value = mock_logging_service
        mock_log_metadata_cls.return_value = mock_log_metadata

        # Execute the function
        result = await create_presentation_node(
            mock_presentation_state,
            mock_slide_config,
            store=mock_base_store
        )

        # Assertions
        assert "error" in result
        assert result["error"] is not None
        assert "Failed to create presentation" in result["error"]
        assert "Database connection failed" in result["error"]

        # Verify handler was called
        mock_handler_cls.assert_called_once()
        mock_presentation_handler_failure.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_presentation_node_with_minimal_state(
        self,
        mock_slide_config,
        mock_base_store
    ):
        """Test presentation creation with minimal state."""

        minimal_state = PresentationState(
            prompt="Simple test prompt",
            n_slides=3,
            language="en",
            documents=None,
            research_reports=None,
            images=None,
            presentation_id=None,
            presentation=None,
            error=None
        )

        with patch('slide_graph.graph.GeneratePresentationRequirementsHandler') as mock_handler_cls:
            mock_handler = MagicMock()
            mock_presentation = PresentationSqlModel(
                id="test-id",
                prompt="Simple test prompt",
                n_slides=3,
                language="en",
                summary="Test summary"
            )
            mock_handler.post = AsyncMock(return_value=mock_presentation)
            mock_handler_cls.return_value = mock_handler

            with patch('slide_graph.graph.LoggingService'), \
                    patch('slide_graph.graph.LogMetadata'):

                result = await create_presentation_node(
                    minimal_state,
                    mock_slide_config,
                    store=mock_base_store
                )

                # Assertions
                assert result["error"] is None
                assert result["presentation"] == mock_presentation
                assert result["presentation_id"] is not None


class TestGenerateTitlesNode:
    """Test the generate_titles_node function."""

    @pytest.fixture
    def mock_titles_handler_success(self, mock_presentation_sql_model):
        """Mock successful titles handler."""
        mock_handler = MagicMock()
        mock_handler.post = AsyncMock(return_value=mock_presentation_sql_model)
        return mock_handler

    @pytest.fixture
    def mock_titles_handler_failure(self):
        """Mock failed titles handler."""
        mock_handler = MagicMock()
        mock_handler.post = AsyncMock(
            side_effect=Exception("Title generation failed"))
        return mock_handler

    @pytest.mark.asyncio
    @patch('slide_graph.graph.PresentationTitlesGenerateHandler')
    @patch('slide_graph.graph.LoggingService')
    @patch('slide_graph.graph.LogMetadata')
    async def test_generate_titles_node_success(
        self,
        mock_log_metadata_cls,
        mock_logging_service_cls,
        mock_handler_cls,
        mock_presentation_state_with_id,
        mock_slide_config,
        mock_base_store,
        mock_titles_handler_success,
        mock_presentation_sql_model,
        mock_logging_service,
        mock_log_metadata
    ):
        """Test successful title generation."""

        # Setup mocks
        mock_handler_cls.return_value = mock_titles_handler_success
        mock_logging_service_cls.return_value = mock_logging_service
        mock_log_metadata_cls.return_value = mock_log_metadata

        # Execute the function
        result = await generate_titles_node(
            mock_presentation_state_with_id,
            mock_slide_config,
            store=mock_base_store
        )

        # Assertions
        assert "presentation" in result
        assert result["presentation"] == mock_presentation_sql_model
        assert "error" in result
        assert result["error"] is None

        # Verify handler was called correctly
        mock_handler_cls.assert_called_once()
        mock_titles_handler_success.post.assert_called_once_with(
            mock_logging_service, mock_log_metadata
        )

    @pytest.mark.asyncio
    @patch('slide_graph.graph.PresentationTitlesGenerateHandler')
    @patch('slide_graph.graph.LoggingService')
    @patch('slide_graph.graph.LogMetadata')
    async def test_generate_titles_node_failure(
        self,
        mock_log_metadata_cls,
        mock_logging_service_cls,
        mock_handler_cls,
        mock_presentation_state_with_id,
        mock_slide_config,
        mock_base_store,
        mock_titles_handler_failure,
        mock_logging_service,
        mock_log_metadata
    ):
        """Test title generation failure."""

        # Setup mocks
        mock_handler_cls.return_value = mock_titles_handler_failure
        mock_logging_service_cls.return_value = mock_logging_service
        mock_log_metadata_cls.return_value = mock_log_metadata

        # Execute the function
        result = await generate_titles_node(
            mock_presentation_state_with_id,
            mock_slide_config,
            store=mock_base_store
        )

        # Assertions
        assert "error" in result
        assert result["error"] is not None
        assert "Failed to generate titles" in result["error"]
        assert "Title generation failed" in result["error"]

        # Verify handler was called
        mock_handler_cls.assert_called_once()
        mock_titles_handler_failure.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_titles_node_no_presentation_id(
        self,
        mock_presentation_state,
        mock_slide_config,
        mock_base_store
    ):
        """Test title generation when no presentation ID is available."""

        # Execute the function
        result = await generate_titles_node(
            mock_presentation_state,
            mock_slide_config,
            store=mock_base_store
        )

        # Assertions
        assert "error" in result
        assert result["error"] is not None
        assert "No presentation ID available from previous step" in result["error"]


class TestCompiledGraph:
    """Test the compiled slide graph."""

    @pytest.mark.asyncio
    @patch('slide_graph.graph.GeneratePresentationRequirementsHandler')
    @patch('slide_graph.graph.PresentationTitlesGenerateHandler')
    @patch('slide_graph.graph.LoggingService')
    @patch('slide_graph.graph.LogMetadata')
    async def test_compiled_graph_success(
        self,
        mock_log_metadata_cls,
        mock_logging_service_cls,
        mock_titles_handler_cls,
        mock_presentation_handler_cls,
        mock_presentation_state,
        mock_slide_config,
        mock_presentation_sql_model,
        mock_logging_service,
        mock_log_metadata
    ):
        """Test successful execution of the compiled graph."""

        # Setup mocks for create_presentation_node
        mock_presentation_handler = MagicMock()
        mock_presentation_handler.post = AsyncMock(
            return_value=mock_presentation_sql_model)
        mock_presentation_handler_cls.return_value = mock_presentation_handler

        # Setup mocks for generate_titles_node
        mock_titles_handler = MagicMock()
        mock_updated_presentation = PresentationSqlModel(
            id=mock_presentation_sql_model.id,
            prompt=mock_presentation_sql_model.prompt,
            n_slides=mock_presentation_sql_model.n_slides,
            language=mock_presentation_sql_model.language,
            summary=mock_presentation_sql_model.summary,
            title="AI in Business: Transforming Industries",
            titles=["Introduction", "AI Applications",
                    "Benefits", "Challenges", "Future Outlook"]
        )
        mock_titles_handler.post = AsyncMock(
            return_value=mock_updated_presentation)
        mock_titles_handler_cls.return_value = mock_titles_handler

        # Setup logging mocks
        mock_logging_service_cls.return_value = mock_logging_service
        mock_log_metadata_cls.return_value = mock_log_metadata

        # Execute the graph
        result = await graph.ainvoke(
            mock_presentation_state,
            config={"configurable": mock_slide_config.__dict__}
        )

        # Assertions
        assert "presentation_id" in result
        assert result["presentation_id"] is not None
        assert "presentation" in result
        assert result["presentation"] == mock_updated_presentation
        assert "error" in result
        assert result["error"] is None

        # Verify both handlers were called
        mock_presentation_handler_cls.assert_called_once()
        mock_titles_handler_cls.assert_called_once()
        mock_presentation_handler.post.assert_called_once()
        mock_titles_handler.post.assert_called_once()

    @pytest.mark.asyncio
    @patch('slide_graph.graph.GeneratePresentationRequirementsHandler')
    @patch('slide_graph.graph.LoggingService')
    @patch('slide_graph.graph.LogMetadata')
    async def test_compiled_graph_create_presentation_failure(
        self,
        mock_log_metadata_cls,
        mock_logging_service_cls,
        mock_presentation_handler_cls,
        mock_presentation_state,
        mock_slide_config,
        mock_logging_service,
        mock_log_metadata
    ):
        """Test graph execution when create_presentation_node fails."""

        # Setup mocks for create_presentation_node failure
        mock_presentation_handler = MagicMock()
        mock_presentation_handler.post = AsyncMock(
            side_effect=Exception("Create presentation failed"))
        mock_presentation_handler_cls.return_value = mock_presentation_handler

        # Setup logging mocks
        mock_logging_service_cls.return_value = mock_logging_service
        mock_log_metadata_cls.return_value = mock_log_metadata

        # Execute the graph
        result = await graph.ainvoke(
            mock_presentation_state,
            config={"configurable": mock_slide_config.__dict__}
        )

        # Assertions
        assert "error" in result
        assert result["error"] is not None
        assert "Failed to create presentation" in result["error"]

        # Verify create_presentation_handler was called
        mock_presentation_handler_cls.assert_called_once()
        mock_presentation_handler.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_compiled_graph_properties(self):
        """Test that the compiled graph has the expected properties."""

        # Test graph name
        assert graph.name == "slide_graph"

        # Test graph structure
        assert hasattr(graph, 'nodes')
        assert hasattr(graph, 'edges')

        # Test that nodes exist
        node_names = [node for node in graph.nodes.keys()]
        assert "create_presentation" in node_names
        assert "generate_titles" in node_names

    @pytest.mark.asyncio
    @patch('slide_graph.graph.GeneratePresentationRequirementsHandler')
    @patch('slide_graph.graph.PresentationTitlesGenerateHandler')
    @patch('slide_graph.graph.LoggingService')
    @patch('slide_graph.graph.LogMetadata')
    async def test_compiled_graph_with_empty_optional_fields(
        self,
        mock_log_metadata_cls,
        mock_logging_service_cls,
        mock_titles_handler_cls,
        mock_presentation_handler_cls,
        mock_slide_config,
        mock_logging_service,
        mock_log_metadata
    ):
        """Test graph execution with empty optional fields."""

        # Create state with empty optional fields
        state = PresentationState(
            prompt="Test presentation",
            n_slides=3,
            language="en",
            documents=None,
            research_reports=None,
            images=None,
            presentation_id=None,
            presentation=None,
            error=None
        )

        # Setup mocks
        test_id = str(uuid.uuid4())
        mock_presentation = PresentationSqlModel(
            id=test_id,
            prompt="Test presentation",
            n_slides=3,
            language="en",
            summary="Test summary"
        )

        mock_presentation_handler = MagicMock()
        mock_presentation_handler.post = AsyncMock(
            return_value=mock_presentation)
        mock_presentation_handler_cls.return_value = mock_presentation_handler

        mock_titles_handler = MagicMock()
        mock_updated_presentation = PresentationSqlModel(
            id=test_id,
            prompt="Test presentation",
            n_slides=3,
            language="en",
            summary="Test summary",
            title="Test Presentation Title",
            titles=["Title 1", "Title 2", "Title 3"]
        )
        mock_titles_handler.post = AsyncMock(
            return_value=mock_updated_presentation)
        mock_titles_handler_cls.return_value = mock_titles_handler

        mock_logging_service_cls.return_value = mock_logging_service
        mock_log_metadata_cls.return_value = mock_log_metadata

        # Execute the graph
        result = await graph.ainvoke(
            state,
            config={"configurable": mock_slide_config.__dict__}
        )

        # Assertions
        assert result["error"] is None
        assert result["presentation"] == mock_updated_presentation
        assert result["presentation_id"] is not None


class TestSlideGraphIntegration:
    """Integration tests for the slide graph workflow."""

    @pytest.fixture
    def complete_presentation_workflow_mocks(self, mock_presentation_sql_model):
        """Setup complete mocks for presentation workflow."""

        # Mock document loading and summary generation
        mock_doc_loader = MagicMock()
        mock_doc_loader.documents = ["Document content"]

        # Mock presentation creation
        mock_presentation_handler = MagicMock()
        mock_presentation_handler.post = AsyncMock(
            return_value=mock_presentation_sql_model)

        # Mock title generation
        mock_titles_handler = MagicMock()
        updated_presentation = PresentationSqlModel(
            id=mock_presentation_sql_model.id,
            prompt=mock_presentation_sql_model.prompt,
            n_slides=mock_presentation_sql_model.n_slides,
            language=mock_presentation_sql_model.language,
            summary=mock_presentation_sql_model.summary,
            title="Complete AI Business Presentation",
            titles=["Introduction", "Current State",
                    "Opportunities", "Implementation", "Conclusion"]
        )
        mock_titles_handler.post = AsyncMock(return_value=updated_presentation)

        return {
            "presentation_handler": mock_presentation_handler,
            "titles_handler": mock_titles_handler,
            "updated_presentation": updated_presentation
        }

    @pytest.mark.asyncio
    @patch('slide_graph.graph.GeneratePresentationRequirementsHandler')
    @patch('slide_graph.graph.PresentationTitlesGenerateHandler')
    @patch('slide_graph.graph.LoggingService')
    @patch('slide_graph.graph.LogMetadata')
    async def test_end_to_end_workflow(
        self,
        mock_log_metadata_cls,
        mock_logging_service_cls,
        mock_titles_handler_cls,
        mock_presentation_handler_cls,
        mock_presentation_state,
        mock_slide_config,
        complete_presentation_workflow_mocks,
        mock_logging_service,
        mock_log_metadata
    ):
        """Test complete end-to-end workflow."""

        # Setup all mocks
        mock_presentation_handler_cls.return_value = complete_presentation_workflow_mocks[
            "presentation_handler"]
        mock_titles_handler_cls.return_value = complete_presentation_workflow_mocks[
            "titles_handler"]
        mock_logging_service_cls.return_value = mock_logging_service
        mock_log_metadata_cls.return_value = mock_log_metadata

        # Execute the complete workflow
        result = await graph.ainvoke(
            mock_presentation_state,
            config={"configurable": mock_slide_config.__dict__}
        )

        # Comprehensive assertions
        assert result["error"] is None
        assert result["presentation_id"] is not None
        assert result["presentation"] == complete_presentation_workflow_mocks["updated_presentation"]

        # Check that the presentation has been fully processed
        final_presentation = result["presentation"]
        assert final_presentation.title is not None
        assert final_presentation.titles is not None
        assert len(final_presentation.titles) == 5
        assert final_presentation.summary is not None

        # Verify all handlers were called in the correct sequence
        complete_presentation_workflow_mocks["presentation_handler"].post.assert_called_once(
        )
        complete_presentation_workflow_mocks["titles_handler"].post.assert_called_once(
        )

        # Verify the state flow - presentation_id should be set after first node
        assert result["presentation_id"] == final_presentation.id
