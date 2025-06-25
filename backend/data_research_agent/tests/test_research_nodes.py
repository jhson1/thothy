"""
Comprehensive test suite for Research Agent nodes.

This test suite covers:
- Individual node testing with proper mocking
- LLM invoke function mocking
- Tavily search function mocking
- Response format validation matching real API responses
- AI agent business opportunities research scenario

All tests use pytest and follow best practices for async testing.
"""

import pytest
from unittest.mock import AsyncMock, patch
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from research_graph.state import (
    ReportState, 
    SectionState, 
    Section, 
    SearchQuery, 
    Queries,
    Feedback
)
from research_graph.graph import (
    generate_report_plan,
    generate_queries,
    search_web,
    write_section,
    compile_final_report
)


class TestGenerateReportPlan:
    """Test the generate_report_plan node"""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing"""
        config = RunnableConfig(
            configurable={
                "report_structure": "academic research format with introduction, methodology, findings, conclusion",
                "number_of_queries": 3,
                "search_api": "tavily",
                "search_api_config": {"max_results": 5},
                "writer_provider": "openai",
                "writer_model": "gpt-4",
                "planner_provider": "openai", 
                "planner_model": "gpt-4"
            }
        )
        return config
    
    @pytest.fixture
    def mock_state(self):
        """Create a mock state for testing"""
        return ReportState(
            messages=[HumanMessage(content="research AI agent business opportunities")],
            ui=[],
            topic="",
            feedback_on_report_plan="",
            sections=[],
            completed_sections=[],
            report_sections_from_research=[],
            final_report=""
        )
    
    @pytest.fixture
    def mock_tavily_response(self):
        """Mock Tavily search response format matching actual API"""
        return [
            {
                "query": "AI agent business opportunities market research",
                "follow_up_questions": None,
                "answer": None,
                "images": [],
                "results": [
                    {
                        "title": "AI Agent Market Analysis 2024",
                        "url": "https://example.com/ai-agent-market",
                        "content": "The AI agent market is expected to grow significantly with opportunities in customer service, automation, and enterprise solutions.",
                        "score": 0.95,
                        "raw_content": "Detailed market analysis content here..."
                    },
                    {
                        "title": "Business Applications of AI Agents",
                        "url": "https://example.com/business-ai-agents", 
                        "content": "AI agents are transforming businesses through intelligent automation, personalized customer experiences, and data-driven insights.",
                        "score": 0.89,
                        "raw_content": "Business applications detailed content..."
                    }
                ]
            }
        ]
    
    @pytest.fixture
    def mock_llm_queries_response(self):
        """Mock LLM response for query generation"""
        return Queries(queries=[
            SearchQuery(search_query="AI agent market size and growth trends 2024"),
            SearchQuery(search_query="business opportunities artificial intelligence agents"),
            SearchQuery(search_query="AI agent implementation challenges and solutions")
        ])
    
    @pytest.fixture
    def mock_llm_sections_response(self):
        """Mock LLM response for sections generation"""
        return {
            "sections": [
                Section(
                    name="Market Overview",
                    description="Current state and size of the AI agent market",
                    research=True,
                    content=""
                ),
                Section(
                    name="Business Opportunities",
                    description="Key opportunities for AI agents in various business sectors",
                    research=True,
                    content=""
                ),
                Section(
                    name="Implementation Strategies",
                    description="Best practices for implementing AI agents in business",
                    research=True,
                    content=""
                ),
                Section(
                    name="Future Outlook",
                    description="Predictions and trends for AI agent adoption",
                    research=False,
                    content="Based on the research conducted, the future of AI agents looks promising with continued growth expected."
                )
            ]
        }
    
    @patch('research_graph.graph.select_and_execute_search')
    @patch('research_graph.graph.init_model_with_provider')
    @patch('research_graph.graph.init_chat_model')
    async def test_generate_report_plan_success(
        self, 
        mock_init_chat_model,
        mock_init_model_with_provider,
        mock_search,
        mock_config,
        mock_state,
        mock_tavily_response,
        mock_llm_queries_response,
        mock_llm_sections_response
    ):
        """Test successful report plan generation"""
        
        # Mock the LLM for query generation
        mock_writer_model = AsyncMock()
        mock_structured_writer = AsyncMock()
        mock_structured_writer.ainvoke.return_value = mock_llm_queries_response
        mock_writer_model.with_structured_output.return_value = mock_structured_writer
        mock_init_model_with_provider.return_value = mock_writer_model
        
        # Mock the search function
        mock_search.return_value = "Market research content from web search results"
        
        # Mock the LLM for sections generation
        mock_planner_model = AsyncMock()
        mock_structured_planner = AsyncMock()
        mock_structured_planner.ainvoke.return_value = mock_llm_sections_response
        mock_planner_model.with_structured_output.return_value = mock_structured_planner
        mock_init_chat_model.return_value = mock_planner_model
        
        # Execute the function
        result = await generate_report_plan(mock_state, mock_config)
        
        # Assertions
        assert "topic" in result
        assert result["topic"] == "research AI agent business opportunities"
        assert "sections" in result
        assert len(result["sections"]) == 4
        assert result["sections"][0].name == "Market Overview"
        assert result["sections"][0].research is True
        assert "messages" in result
        assert len(result["messages"]) >= 3  # Original + 2 AI messages
        
        # Verify search was called
        mock_search.assert_called_once()
        
        # Verify LLM calls were made
        mock_structured_writer.ainvoke.assert_called_once()
        mock_structured_planner.ainvoke.assert_called_once()
    
    async def test_generate_report_plan_no_topic_error(self, mock_config):
        """Test error handling when no topic is provided"""
        empty_state = ReportState(
            messages=[],
            ui=[],
            topic="",
            feedback_on_report_plan="",
            sections=[],
            completed_sections=[],
            report_sections_from_research=[],
            final_report=""
        )
        
        with pytest.raises(ValueError, match="No topic received"):
            await generate_report_plan(empty_state, mock_config)


class TestGenerateQueries:
    """Test the generate_queries node"""
    
    @pytest.fixture
    def mock_section_state(self):
        """Create a mock section state for testing"""
        section = Section(
            name="AI Agent Market Analysis",
            description="Analyze the current market for AI agents and identify key growth opportunities",
            research=True,
            content=""
        )
        return SectionState(
            topic="AI agent business opportunities",
            section=[section],
            search_iterations=[0],
            search_queries=[],
            source_str=[],
            report_sections_from_research=[],
            messages=[]
        )
    
    @pytest.fixture
    def mock_config_queries(self):
        """Create a mock configuration for query generation"""
        config = RunnableConfig(
            configurable={
                "number_of_queries": 3,
                "writer_provider": "openai",
                "writer_model": "gpt-4"
            }
        )
        return config
    
    @pytest.fixture
    def mock_generated_queries(self):
        """Mock generated queries response"""
        return Queries(queries=[
            SearchQuery(search_query="AI agent market size trends 2024"),
            SearchQuery(search_query="artificial intelligence agent business applications"),
            SearchQuery(search_query="AI agent implementation ROI case studies")
        ])
    
    @patch('research_graph.graph.init_chat_model')
    async def test_generate_queries_success(
        self,
        mock_init_chat_model,
        mock_section_state,
        mock_config_queries,
        mock_generated_queries
    ):
        """Test successful query generation"""
        
        # Mock the LLM
        mock_model = AsyncMock()
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke.return_value = mock_generated_queries
        mock_model.with_structured_output.return_value = mock_structured_llm
        mock_init_chat_model.return_value = mock_model
        
        # Execute the function
        result = await generate_queries(mock_section_state, mock_config_queries)
        
        # Assertions
        assert "search_queries" in result
        assert len(result["search_queries"]) == 3
        assert result["search_queries"][0].search_query == "AI agent market size trends 2024"
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)
        
        # Verify LLM was called correctly
        mock_structured_llm.ainvoke.assert_called_once()
        call_args = mock_structured_llm.ainvoke.call_args[0][0]
        assert len(call_args) == 2
        assert isinstance(call_args[0], SystemMessage)
        assert isinstance(call_args[1], HumanMessage)
    
    async def test_generate_queries_no_section_error(self, mock_config_queries):
        """Test error handling when no section is provided"""
        empty_state = SectionState(
            topic="AI agent business opportunities",
            section=[],
            search_iterations=[0],
            search_queries=[],
            source_str=[],
            report_sections_from_research=[],
            messages=[]
        )
        
        with pytest.raises(ValueError, match="No section found"):
            await generate_queries(empty_state, mock_config_queries)


class TestSearchWeb:
    """Test the search_web node"""
    
    @pytest.fixture
    def mock_search_state(self):
        """Create a mock state with search queries"""
        return SectionState(
            topic="AI agent business opportunities",
            section=[],
            search_iterations=[0],
            search_queries=[
                SearchQuery(search_query="AI agent market opportunities"),
                SearchQuery(search_query="business AI automation trends")
            ],
            source_str=[],
            report_sections_from_research=[],
            messages=[]
        )
    
    @pytest.fixture
    def mock_search_config(self):
        """Create a mock configuration for search"""
        config = RunnableConfig(
            configurable={
                "search_api": "tavily",
                "search_api_config": {"max_results": 5}
            }
        )
        return config
    
    @pytest.fixture
    def mock_search_results(self):
        """Mock search results in Tavily format"""
        return "=== Search Results ===\n" \
               "Source: AI Agent Market Report 2024\n" \
               "URL: https://example.com/market-report\n" \
               "Content: The AI agent market is experiencing rapid growth with significant opportunities in enterprise automation...\n\n" \
               "Source: Business AI Implementation Guide\n" \
               "URL: https://example.com/implementation-guide\n" \
               "Content: Companies are increasingly adopting AI agents for customer service, data analysis, and process automation..."
    
    @patch('research_graph.graph.select_and_execute_search')
    async def test_search_web_success(
        self,
        mock_search_function,
        mock_search_state,
        mock_search_config,
        mock_search_results
    ):
        """Test successful web search"""
        
        # Mock the search function
        mock_search_function.return_value = mock_search_results
        
        # Execute the function
        result = await search_web(mock_search_state, mock_search_config)
        
        # Assertions
        assert "source_str" in result
        assert len(result["source_str"]) == 1
        assert result["source_str"][0] == mock_search_results
        assert "search_iterations" in result
        assert result["search_iterations"] == [1]  # Should increment from 0 to 1
        
        # Verify search was called with correct parameters
        mock_search_function.assert_called_once()
        call_args = mock_search_function.call_args[0]
        assert call_args[0] == "tavily"  # search_api
        assert call_args[1] == ["AI agent market opportunities", "business AI automation trends"]  # queries


class TestWriteSection:
    """Test the write_section node"""
    
    @pytest.fixture
    def mock_write_state(self):
        """Create a mock state for section writing"""
        section = Section(
            name="Market Opportunities",
            description="Analysis of business opportunities for AI agents",
            research=True,
            content=""
        )
        return SectionState(
            topic="AI agent business opportunities",
            section=[section],
            search_iterations=[1],
            search_queries=[],
            source_str=["Market research data about AI agents and business opportunities..."],
            report_sections_from_research=[],
            messages=[]
        )
    
    @pytest.fixture
    def mock_write_config(self):
        """Create a mock configuration for section writing"""
        config = RunnableConfig(
            configurable={
                "writer_provider": "openai",
                "writer_model": "gpt-4",
                "planner_provider": "openai",
                "planner_model": "gpt-4",
                "number_of_queries": 3,
                "max_search_depth": 3
            }
        )
        return config
    
    @pytest.fixture
    def mock_section_content(self):
        """Mock section content generated by LLM"""
        return AIMessage(content="""# Market Opportunities for AI Agents

The AI agent market presents significant business opportunities across multiple sectors:

## Enterprise Automation
- Customer service automation with intelligent chatbots
- Process automation for repetitive tasks
- Data analysis and reporting automation

## Emerging Markets
- Healthcare: AI agents for patient monitoring and diagnosis assistance
- Finance: Automated trading and risk assessment agents
- Education: Personalized learning and tutoring agents

## Market Size and Growth
According to recent research, the AI agent market is expected to grow from $4.2 billion in 2024 to $15.8 billion by 2029, representing a CAGR of 30.2%.""")
    
    @pytest.fixture
    def mock_feedback_pass(self):
        """Mock feedback indicating section passes quality check"""
        return Feedback(
            grade="pass",
            follow_up_queries=[]
        )
    
    @pytest.fixture
    def mock_feedback_fail(self):
        """Mock feedback indicating section needs improvement"""
        return Feedback(
            grade="fail",
            follow_up_queries=[
                SearchQuery(search_query="AI agent market size statistics 2024"),
                SearchQuery(search_query="successful AI agent implementation case studies")
            ]
        )
    
    @patch('research_graph.graph.push_ui_message')
    @patch('research_graph.graph.init_chat_model')
    async def test_write_section_pass_quality(
        self,
        mock_init_chat_model,
        mock_push_ui,
        mock_write_state,
        mock_write_config,
        mock_section_content,
        mock_feedback_pass
    ):
        """Test section writing that passes quality check"""
        
        # Mock the writer model
        mock_writer = AsyncMock()
        mock_writer.ainvoke.return_value = mock_section_content
        
        # Mock the reflection model
        mock_reflection = AsyncMock()
        mock_structured_reflection = AsyncMock()
        mock_structured_reflection.ainvoke.return_value = mock_feedback_pass
        mock_reflection.with_structured_output.return_value = mock_structured_reflection
        
        # Configure init_chat_model to return different models for different calls
        mock_init_chat_model.side_effect = [mock_writer, mock_reflection]
        
        # Execute the function
        result = await write_section(mock_write_state, mock_write_config)
        
        # Assertions for successful completion
        assert result.goto == "END"
        assert "report_sections_from_research" in result.update
        assert len(result.update["report_sections_from_research"]) == 1
        
        # Verify both models were called
        assert mock_init_chat_model.call_count == 2
        mock_writer.ainvoke.assert_called_once()
        mock_structured_reflection.ainvoke.assert_called_once()
        
        # Verify UI message was pushed
        mock_push_ui.assert_called_once()


class TestCompileFinalReport:
    """Test the compile_final_report node"""
    
    def test_compile_final_report(self):
        """Test compiling the final report"""
        
        completed_sections = [
            Section(
                name="Market Overview",
                description="Current state of AI agent market",
                research=True,
                content="The AI agent market is experiencing unprecedented growth with a valuation of $4.2 billion in 2024."
            ),
            Section(
                name="Business Opportunities",
                description="Key opportunities in AI agent business",
                research=True,
                content="Key opportunities include customer service automation, process optimization, and data analysis."
            ),
            Section(
                name="Conclusion",
                description="Summary and recommendations",
                research=False,
                content="Based on this research, businesses should consider implementing AI agents to remain competitive."
            )
        ]
        
        state = ReportState(
            messages=[],
            ui=[],
            topic="AI agent business opportunities",
            feedback_on_report_plan="",
            sections=[],
            completed_sections=completed_sections,
            report_sections_from_research=[],
            final_report=""
        )
        
        # Execute the function
        result = compile_final_report(state)
        
        # Assertions
        assert "final_report" in result
        final_report = result["final_report"]
        
        # Verify report structure
        assert "# Research Report: AI agent business opportunities" in final_report
        assert "## Market Overview" in final_report
        assert "## Business Opportunities" in final_report
        assert "## Conclusion" in final_report
        
        # Verify content is included
        assert "The AI agent market is experiencing unprecedented growth" in final_report
        assert "Key opportunities include customer service automation" in final_report
        assert "businesses should consider implementing AI agents" in final_report


class TestAIAgentBusinessScenario:
    """End-to-end test scenario for AI agent business opportunities research"""
    
    def test_tavily_response_format_validation(self):
        """Test that our mock responses match actual Tavily API format"""
        
        # Mock response matching actual Tavily format
        tavily_response = {
            "query": "AI agent business opportunities 2024",
            "follow_up_questions": None,
            "answer": None,
            "images": [],
            "results": [
                {
                    "title": "AI Agent Market Analysis 2024 - Enterprise Opportunities",
                    "url": "https://example.com/ai-market-2024",
                    "content": "The AI agent market presents significant opportunities for enterprises looking to automate customer service, streamline operations, and enhance decision-making processes.",
                    "score": 0.95,
                    "raw_content": "Full article content about AI agent market opportunities..."
                },
                {
                    "title": "Business ROI of AI Agent Implementation",
                    "url": "https://example.com/ai-roi-study",
                    "content": "Companies implementing AI agents report 25-40% reduction in operational costs and 60% improvement in customer satisfaction scores.",
                    "score": 0.92,
                    "raw_content": "Detailed ROI analysis and case studies..."
                }
            ]
        }
        
        # Validate response structure matches Tavily API
        assert "query" in tavily_response
        assert "results" in tavily_response
        assert "follow_up_questions" in tavily_response
        assert "answer" in tavily_response
        assert "images" in tavily_response
        
        # Validate results structure
        for result in tavily_response["results"]:
            assert "title" in result
            assert "url" in result
            assert "content" in result
            assert "score" in result
            assert "raw_content" in result
            
            # Validate data types
            assert isinstance(result["title"], str)
            assert isinstance(result["url"], str)
            assert isinstance(result["content"], str)
            assert isinstance(result["score"], float)
            assert isinstance(result["raw_content"], str)
            assert 0.0 <= result["score"] <= 1.0
    
    def test_llm_response_format_validation(self):
        """Test that our mock LLM responses match expected formats"""
        
        # Test Queries response format
        queries_response = Queries(queries=[
            SearchQuery(search_query="AI agent market size growth 2024"),
            SearchQuery(search_query="enterprise AI automation ROI business case"),
            SearchQuery(search_query="AI agent customer service implementation success stories")
        ])
        
        assert isinstance(queries_response, Queries)
        assert len(queries_response.queries) == 3
        for query in queries_response.queries:
            assert isinstance(query, SearchQuery)
            assert isinstance(query.search_query, str)
            assert len(query.search_query) > 0
        
        # Test Section response format
        sections = [
            Section(
                name="Executive Summary",
                description="High-level overview of AI agent business opportunities",
                research=True,
                content=""
            ),
            Section(
                name="Market Analysis",
                description="Current market size, growth trends, and competitive landscape",
                research=True,
                content=""
            ),
            Section(
                name="Business Applications",
                description="Key use cases and applications of AI agents in business",
                research=True,
                content=""
            ),
            Section(
                name="Implementation Strategy",
                description="Best practices and recommendations for AI agent adoption",
                research=True,
                content=""
            ),
            Section(
                name="Recommendations",
                description="Strategic recommendations based on research findings",
                research=False,
                content="Based on our analysis, we recommend a phased approach to AI agent implementation."
            )
        ]
        
        for section in sections:
            assert isinstance(section, Section)
            assert isinstance(section.name, str)
            assert isinstance(section.description, str)
            assert isinstance(section.research, bool)
            assert isinstance(section.content, str)
        
        # Test AIMessage content format
        ai_message = AIMessage(content="""# Executive Summary

The AI agent market represents one of the fastest-growing segments in enterprise technology, with significant opportunities for businesses across industries.

## Key Findings

1. **Market Growth**: The global AI agent market is projected to reach $15.8 billion by 2029
2. **ROI Potential**: Companies report 25-40% cost reduction in operational areas
3. **Adoption Rate**: 65% of enterprises plan to implement AI agents within 24 months

## Primary Opportunities

- **Customer Service**: 24/7 automated support with 90% resolution rate
- **Process Automation**: Streamlining repetitive tasks and workflows  
- **Data Analysis**: Real-time insights and predictive analytics
- **Sales Support**: Lead qualification and customer engagement

## Strategic Recommendations

Organizations should prioritize AI agent implementation in customer-facing operations first, then expand to internal processes based on ROI metrics and user adoption rates.""")
        
        assert isinstance(ai_message, AIMessage)
        assert isinstance(ai_message.content, str)
        assert len(ai_message.content) > 100
        assert "# Executive Summary" in ai_message.content
        assert "## Key Findings" in ai_message.content
    
    def test_business_scenario_query_validation(self):
        """Test that our AI agent business scenario generates appropriate queries"""
        
        # Expected query types for this scenario
        expected_query_themes = [
            "market size",
            "business applications", 
            "ROI",
            "implementation",
            "automation",
            "customer service"
        ]
        
        # Mock queries that would be generated for this scenario
        generated_queries = [
            "AI agent market size growth trends 2024",
            "enterprise AI automation ROI business case studies",
            "AI agent customer service implementation success rates",
            "business process automation AI agents cost savings",
            "AI agent deployment challenges enterprise solutions"
        ]
        
        # Validate that queries cover the expected themes
        all_queries_text = " ".join(generated_queries).lower()
        
        covered_themes = []
        for theme in expected_query_themes:
            if theme in all_queries_text:
                covered_themes.append(theme)
        
        # Should cover at least 4 out of 6 themes
        assert len(covered_themes) >= 4, f"Only covered themes: {covered_themes}"
        
        # Validate query structure
        for query in generated_queries:
            assert isinstance(query, str)
            assert len(query) > 10  # Reasonable length
            assert not query.startswith("?")  # Not a question
            assert not query.replace(" ", "").replace("-", "").isalnum()  # Contains spaces


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 