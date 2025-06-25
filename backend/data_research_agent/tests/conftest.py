"""
Pytest configuration and shared fixtures for research agent tests.

This file contains common fixtures and configuration used across all test files.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_async_llm():
    """Create a mock async LLM for testing"""
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AsyncMock()
    return mock_llm


@pytest.fixture
def ai_agent_research_topic():
    """Standard research topic for AI agent business opportunities"""
    return "research AI agent business opportunities for enterprise automation and customer service"


@pytest.fixture
def sample_tavily_search_result():
    """Sample Tavily search result matching actual API format"""
    return {
        "query": "AI agent business opportunities",
        "follow_up_questions": None,
        "answer": None,
        "images": [],
        "results": [
            {
                "title": "AI Agent Market Report 2024",
                "url": "https://example.com/ai-agent-market",
                "content": "The AI agent market presents significant opportunities in enterprise automation, customer service, and data analysis.",
                "score": 0.95,
                "raw_content": "Detailed market analysis content about AI agent opportunities..."
            },
            {
                "title": "Enterprise AI Implementation Guide", 
                "url": "https://example.com/enterprise-ai-guide",
                "content": "Best practices for implementing AI agents in enterprise environments with proven ROI.",
                "score": 0.88,
                "raw_content": "Comprehensive guide for enterprise AI agent deployment..."
            }
        ]
    }


@pytest.fixture
def sample_business_section():
    """Sample business section for AI agent research"""
    from research_graph.state import Section
    
    return Section(
        name="Market Opportunities",
        description="Analysis of business opportunities for AI agents in enterprise markets",
        research=True,
        content=""
    )


@pytest.fixture
def mock_openai_config():
    """Mock configuration for OpenAI models"""
    from langchain_core.runnables import RunnableConfig
    
    return RunnableConfig(
        configurable={
            "writer_provider": "openai",
            "writer_model": "gpt-4",
            "planner_provider": "openai", 
            "planner_model": "gpt-4",
            "number_of_queries": 3,
            "max_search_depth": 2,
            "search_api": "tavily",
            "search_api_config": {"max_results": 5},
            "report_structure": "business research format"
        }
    ) 