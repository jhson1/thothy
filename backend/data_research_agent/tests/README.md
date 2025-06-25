# Research Agent Tests

This directory contains comprehensive tests for the research agent backend, focusing on the AI agent business opportunities research scenario.

## Overview

The test suite covers:
- Individual node process testing with proper mocking
- LLM invoke function mocking with realistic responses
- Tavily search function mocking with actual API response formats
- Response format validation to ensure mock data matches real API responses
- End-to-end scenario testing for AI agent business opportunities research

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Pytest configuration and shared fixtures
├── test_research_nodes.py      # Main test suite for research nodes
├── requirements.txt            # Test dependencies
└── README.md                   # This file
```

## Key Test Classes

### TestGenerateReportPlan
Tests the `generate_report_plan` node which:
- Extracts topic from user messages
- Generates search queries for planning
- Executes web searches
- Uses LLM to generate structured report sections

### TestGenerateQueries
Tests the `generate_queries` node which:
- Takes a section description
- Uses LLM to generate targeted search queries
- Returns structured query objects

### TestSearchWeb
Tests the `search_web` node which:
- Executes search queries using configured search API
- Formats results for section writing
- Handles iteration counting

### TestWriteSection
Tests the `write_section` node which:
- Writes section content using search results
- Evaluates content quality using LLM
- Routes to either completion or more research

### TestCompileFinalReport
Tests the `compile_final_report` node which:
- Combines all completed sections
- Formats final report with proper structure
- Returns complete research report

### TestAIAgentBusinessScenario
End-to-end validation tests including:
- Tavily API response format validation
- LLM response format validation
- Business scenario query validation

## Mock Strategy

### LLM Mocking
- Uses `AsyncMock` to simulate LLM `ainvoke` calls
- Provides realistic structured outputs matching actual LLM responses
- Tests different response formats (Queries, Sections, Feedback)

### Tavily Search Mocking
- Mock responses match actual Tavily API format exactly
- Includes all required fields: query, results, follow_up_questions, answer, images
- Result objects include: title, url, content, score, raw_content
- Validates data types and score ranges (0.0-1.0)

### Configuration Mocking
- Uses `RunnableConfig` with realistic configurable parameters
- Supports different model providers (OpenAI, Anthropic, etc.)
- Includes search API configuration and parameters

## Test Scenario: AI Agent Business Opportunities

The main test scenario focuses on researching AI agent business opportunities with:

**Research Topic**: "research AI agent business opportunities for enterprise automation and customer service"

**Expected Sections**:
- Market Overview
- Business Opportunities  
- Implementation Strategies
- Future Outlook

**Mock Search Results**: Realistic content about AI agent market trends, ROI studies, and implementation guides

**Expected Queries**: Market size, business applications, ROI, implementation strategies

## Running Tests

### Prerequisites
```bash
cd backend/research_agent/tests
pip install -r requirements.txt
```

### Run All Tests
```bash
pytest test_research_nodes.py -v
```

### Run Specific Test Class
```bash
pytest test_research_nodes.py::TestGenerateReportPlan -v
```

### Run with Coverage
```bash
pytest test_research_nodes.py --cov=research_graph --cov-report=html
```

### Run Async Tests Only
```bash
pytest test_research_nodes.py -k "async" -v
```

### Run Business Scenario Tests
```bash
pytest test_research_nodes.py::TestAIAgentBusinessScenario -v
```

## Expected Test Output

Tests should validate:
✅ Topic extraction from messages
✅ LLM query generation with 3 search queries
✅ Tavily search execution with proper parameters
✅ Section content generation with realistic business content
✅ Quality evaluation and routing decisions
✅ Final report compilation with proper structure
✅ Response format validation matching real APIs

## Mock Response Validation

The tests include validation that mock responses match real API formats:

**Tavily Response Structure**:
```json
{
  "query": "search query",
  "follow_up_questions": null,
  "answer": null, 
  "images": [],
  "results": [
    {
      "title": "Result Title",
      "url": "https://example.com",
      "content": "Result content snippet",
      "score": 0.95,
      "raw_content": "Full page content"
    }
  ]
}
```

**LLM Response Validation**:
- Queries: Structured `Queries` object with `SearchQuery` list
- Sections: List of `Section` objects with name, description, research flag, content
- Content: `AIMessage` with substantial text content (>100 chars)
- Feedback: `Feedback` object with grade ("pass"/"fail") and follow-up queries

## Debugging Tests

For debugging failed tests:

```bash
# Run with detailed output
pytest test_research_nodes.py -v -s

# Run single test with debugging
pytest test_research_nodes.py::TestGenerateReportPlan::test_generate_report_plan_success -v -s

# Show local variables on failure
pytest test_research_nodes.py --tb=long
```

## Adding New Tests

When adding new tests:
1. Follow the existing naming convention: `test_<node_name>_<scenario>`
2. Use appropriate fixtures from `conftest.py`
3. Mock external dependencies (LLM calls, search APIs)
4. Validate response formats match real APIs
5. Include error handling tests
6. Add docstrings explaining test purpose

## Test Data

All test data should represent realistic business scenarios:
- Use actual AI agent market trends and opportunities
- Include realistic ROI figures and case studies
- Cover enterprise automation and customer service use cases
- Reflect current market conditions and growth projections 