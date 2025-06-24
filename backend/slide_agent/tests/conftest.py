"""
Pytest configuration and shared fixtures for slide_agent tests.

This file contains common fixtures and configuration used across all test files.
"""

import pytest
import uuid
from unittest.mock import MagicMock
from langchain_core.runnables import RunnableConfig

from slide_graph.graph import PresentationState
from slide_graph.configuration import SlideConfigurable
from slide_graph.api.sql_models import PresentationSqlModel
from slide_graph.api.models import LogMetadata
from slide_graph.api.routers.presentation.models import (
    GeneratePresentationRequirementsRequest,
    GenerateTitleRequest,
)


@pytest.fixture
def mock_presentation_id():
    """Generate a mock presentation ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def mock_slide_config():
    """Create a mock SlideConfigurable for testing."""
    return SlideConfigurable(
        model="gpt-4o-mini",
        system_prompt="You are a helpful presentation assistant."
    )


@pytest.fixture
def mock_runnable_config():
    """Create a mock RunnableConfig for testing."""
    return RunnableConfig(
        configurable={
            "model": "gpt-4o-mini",
            "system_prompt": "You are a helpful presentation assistant."
        }
    )


@pytest.fixture
def mock_presentation_state():
    """Create a mock PresentationState for testing."""
    return PresentationState(
        prompt="Create a presentation about AI in business",
        n_slides=5,
        language="en",
        documents=["document1.pdf", "document2.pdf"],
        research_reports=["report1.pdf"],
        images=["image1.jpg"],
        presentation_id=None,
        presentation=None,
        error=None
    )


@pytest.fixture
def mock_presentation_sql_model(mock_presentation_id):
    """Create a mock PresentationSqlModel for testing."""
    return PresentationSqlModel(
        id=mock_presentation_id,
        prompt="Create a presentation about AI in business",
        n_slides=5,
        language="en",
        summary="AI in business presentation covering key topics",
        title="AI in Business: Transforming Industries",
        titles=["Introduction", "AI Applications", "Benefits", "Challenges", "Future Outlook"]
    )


@pytest.fixture
def mock_logging_service():
    """Create a mock LoggingService for testing."""
    mock_service = MagicMock()
    mock_service.logger = MagicMock()
    mock_service.message = MagicMock(return_value="Test log message")
    return mock_service


@pytest.fixture
def mock_log_metadata(mock_presentation_id):
    """Create a mock LogMetadata for testing."""
    return LogMetadata(
        presentation_id=mock_presentation_id,
        endpoint="/test/endpoint"
    )


@pytest.fixture
def mock_generate_presentation_request():
    """Create a mock GeneratePresentationRequirementsRequest for testing."""
    return GeneratePresentationRequirementsRequest(
        prompt="Create a presentation about AI in business",
        n_slides=5,
        language="en",
        documents=["document1.pdf", "document2.pdf"],
        research_reports=["report1.pdf"],
        images=["image1.jpg"]
    )


@pytest.fixture
def mock_generate_title_request(mock_presentation_id):
    """Create a mock GenerateTitleRequest for testing."""
    return GenerateTitleRequest(
        presentation_id=mock_presentation_id
    )


@pytest.fixture
def mock_base_store():
    """Create a mock BaseStore for testing."""
    return MagicMock()


@pytest.fixture
def mock_presentation_state_with_id(mock_presentation_id, mock_presentation_sql_model):
    """Create a mock PresentationState with presentation_id set."""
    return PresentationState(
        prompt="Create a presentation about AI in business",
        n_slides=5,
        language="en",
        documents=["document1.pdf", "document2.pdf"],
        research_reports=["report1.pdf"],
        images=["image1.jpg"],
        presentation_id=mock_presentation_id,
        presentation=mock_presentation_sql_model,
        error=None
    )


@pytest.fixture
def mock_presentation_state_empty():
    """Create an empty PresentationState for testing error conditions."""
    return PresentationState(
        prompt=None,
        n_slides=0,
        language="en",
        documents=None,
        research_reports=None,
        images=None,
        presentation_id=None,
        presentation=None,
        error=None
    ) 